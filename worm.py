#!/usr/bin/env python3
"""
worm - 通过邮箱发送文件的命令行工具

用法:
  worm <文件或目录路径> <目标邮箱>
  worm setup          自动配置全局命令与配置文件
  worm setup --check  检查当前配置状态
"""

import sys
import os
import smtplib
import configparser
import mimetypes
import shutil
import tempfile
import platform
import stat
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.encoders import encode_base64
from email.utils import formataddr, formatdate
from pathlib import Path


WORM_SCRIPT = Path(__file__).resolve()
CONF_NAME = "worm.conf"
MAX_ATTACH_SIZE = 50 * 1024 * 1024


def _system():
    return platform.system().lower()


def _user_config_path():
    if _system() == "windows":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / "worm" / CONF_NAME
    return Path.home() / ".config" / "worm" / CONF_NAME


def _example_config_path():
    return WORM_SCRIPT.parent / "worm.conf.example"


_DEFAULT_TEMPLATE = (
    "[smtp]\n"
    "smtp_host = smtp.qq.com\n"
    "smtp_port = 465\n"
    "smtp_user = your_email@example.com\n"
    "smtp_pass = your_auth_code\n"
    "sender_name = Worm\n"
)

_PLACEHOLDER_VALUES = {
    "your_email@example.com",
    "your_auth_code",
}


def _dir_in_path(target_dir):
    target = os.path.normcase(os.path.normpath(target_dir))
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.normcase(os.path.normpath(entry)) == target:
            return True
    return False


def _check_config_fields(cfg_path):
    cfg = configparser.ConfigParser()
    cfg.read(str(cfg_path), encoding="utf-8")
    required = ["smtp_host", "smtp_port", "smtp_user", "smtp_pass"]
    missing = [k for k in required if not cfg.has_option("smtp", k)]
    unfilled = []
    for key in required:
        if cfg.has_option("smtp", key):
            val = cfg.get("smtp", key).strip()
            if val in _PLACEHOLDER_VALUES or not val:
                unfilled.append(key)
    return missing, unfilled


def find_config():
    candidates = [
        _user_config_path(),
        Path.home() / f".{CONF_NAME}",
        Path(__file__).resolve().parent / CONF_NAME,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config():
    path = find_config()
    if path is None:
        print(f"❌ 找不到配置文件。请将配置文件放在以下任意位置：")
        print(f"   1. {_user_config_path()}")
        print(f"   2. ~/.{CONF_NAME}")
        print(f"   3. {Path(__file__).resolve().parent / CONF_NAME}")
        print("\n可运行 worm setup 自动生成配置文件。")
        sys.exit(1)

    cfg = configparser.ConfigParser()
    cfg.read(str(path), encoding="utf-8")

    required = ["smtp_host", "smtp_port", "smtp_user", "smtp_pass"]
    for key in required:
        if not cfg.has_option("smtp", key):
            print(f"❌ 配置文件缺少字段: {key}  ({path})")
            sys.exit(1)

    return {
        "host": cfg.get("smtp", "smtp_host"),
        "port": cfg.getint("smtp", "smtp_port"),
        "user": cfg.get("smtp", "smtp_user"),
        "password": cfg.get("smtp", "smtp_pass"),
        "sender_name": cfg.get("smtp", "sender_name", fallback="Worm"),
    }


def zip_directory(dirpath):
    dirpath = os.path.realpath(dirpath)
    dirname = os.path.basename(dirpath.rstrip(os.sep))
    if not os.listdir(dirpath):
        print(f"❌ 目录为空: {dirpath}")
        sys.exit(1)
    tmpdir = tempfile.mkdtemp()
    zip_base = os.path.join(tmpdir, dirname)
    print(f"📦 正在打包目录 {dirname}/ ...")
    zip_path = shutil.make_archive(zip_base, "zip", root_dir=os.path.dirname(dirpath), base_dir=dirname)
    return zip_path, tmpdir


def cleanup_temp(tmpdir):
    try:
        shutil.rmtree(tmpdir)
    except OSError:
        pass


def build_message(smtp_cfg, filepath, recipient):
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    size_str = (
        f"{filesize / 1024 / 1024:.1f} MB" if filesize > 1024 * 1024
        else f"{filesize / 1024:.1f} KB" if filesize > 1024
        else f"{filesize} B"
    )

    msg = MIMEMultipart()
    msg["From"] = formataddr((smtp_cfg["sender_name"], smtp_cfg["user"]))
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = f"文件发送: {filename}"

    body = f"附件: {filename}\n大小: {size_str}\n\n此邮件由 worm 工具自动发送。"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(filepath, "rb") as fh:
        part = MIMEBase(maintype, subtype)
        part.set_payload(fh.read())
    encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    return msg


def send(smtp_cfg, msg, recipient):
    host = smtp_cfg["host"]
    port = smtp_cfg["port"]

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        try:
            server.starttls()
        except smtplib.SMTPNotSupportedError:
            pass

    try:
        server.login(smtp_cfg["user"], smtp_cfg["password"])
        server.sendmail(smtp_cfg["user"], [recipient], msg.as_string())
    finally:
        server.quit()


def print_usage():
    prog = os.path.basename(sys.argv[0])
    cfg_hint = _user_config_path()
    print(f"""用法:
  {prog} <文件或目录路径> <目标邮箱>   发送文件/目录到邮箱
  {prog} setup                         自动配置全局命令
  {prog} setup --check                 检查配置状态

示例:
  {prog} ./report.pdf zhangsan@qq.com
  {prog} ./project_dir zhangsan@qq.com
  {prog} /var/log/app.log admin@163.com

配置:
  首次使用前，运行 {prog} setup 自动生成配置文件，
  或复制 worm.conf.example 并填写 SMTP 信息。
  配置文件搜索顺序：
    1. {cfg_hint}
    2. ~/.worm.conf
    3. 程序同目录/worm.conf
""")


# ---------------------------------------------------------------------------
#  跨平台全局安装 / 配置向导
# ---------------------------------------------------------------------------

def _install_link_unix():
    link_path = Path("/usr/local/bin/worm")
    target = WORM_SCRIPT

    if not os.access(target, os.X_OK):
        try:
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"  ✅ 已为 {target} 添加可执行权限")
        except PermissionError:
            print(f"  ⚠️  无法为 {target} 添加可执行权限，请手动运行：")
            print(f"       sudo chmod +x {target}")
            return False

    if link_path.exists() or link_path.is_symlink():
        real = None
        try:
            real = link_path.resolve()
        except OSError:
            pass
        if real == target:
            print(f"  ✅ 全局命令已就绪: {link_path} → {target}")
            return True
        else:
            print(f"  ⚠️  {link_path} 已存在但指向 {real}")
            print(f"     请先手动删除: sudo rm {link_path}")
            print(f"     然后重新运行 setup。")
            return False

    try:
        link_path.symlink_to(target)
        print(f"  ✅ 已创建符号链接: {link_path} → {target}")
        return True
    except PermissionError:
        print(f"  ❌ 没有权限创建 {link_path}")
        print(f"     请使用管理员权限运行：")
        print(f"       sudo python3 {WORM_SCRIPT} setup")
        print(f"     或者手动创建：")
        print(f"       sudo ln -sf {target} {link_path}")
        return False


def _install_windows():
    worm_dir = str(WORM_SCRIPT.parent)
    cmd_path = WORM_SCRIPT.parent / "worm.cmd"

    if not cmd_path.exists():
        cmd_content = '@echo off\r\npython "' + str(WORM_SCRIPT) + '" %*\r\n'
        try:
            cmd_path.write_text(cmd_content, encoding="utf-8")
            print(f"  ✅ 已创建启动脚本: {cmd_path}")
        except PermissionError:
            print(f"  ❌ 无法写入 {cmd_path}，请检查目录权限。")
            return False
    else:
        print(f"  ✅ 启动脚本已存在: {cmd_path}")

    if _dir_in_path(worm_dir):
        print(f"  ✅ 目录已在 PATH 中: {worm_dir}")
        return True

    try:
        worm_dir_lower = worm_dir.lower()
        ps_script = (
            '$old = [Environment]::GetEnvironmentVariable("PATH","User");'
            'if($old -and ($old.ToLower().Split(";") -contains "'
            + worm_dir_lower
            + '")){"already"}'
            'elseif($old){[Environment]::SetEnvironmentVariable("PATH","$old;'
            + worm_dir
            + '","User");"added"}'
            'else{[Environment]::SetEnvironmentVariable("PATH","'
            + worm_dir
            + '","User");"added"}'
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )
        out = result.stdout.strip()
        if out == "added":
            print(f"  ✅ 已将 {worm_dir} 添加到用户 PATH（重启终端生效）")
            return True
        elif out == "already":
            print(f"  ✅ 目录已在用户 PATH 中: {worm_dir}")
            return True
        else:
            raise RuntimeError(result.stderr or "unknown error")
    except Exception as exc:
        print(f"  ❌ 无法自动设置 PATH: {exc}")
        print(f"     请手动将以下目录加入系统环境变量 PATH：")
        print(f"       {worm_dir}")
        print("     步骤: 设置 → 系统 → 关于 → 高级系统设置 → 环境变量 → PATH → 编辑 → 新建")
        return False


def setup_global_command():
    sys_name = _system()
    print("\n🔧 [1/2] 注册全局命令 worm ...")
    if sys_name in ("linux", "darwin"):
        return _install_link_unix()
    elif sys_name == "windows":
        return _install_windows()
    else:
        print(f"  ⚠️  未识别的操作系统: {platform.system()}，跳过全局命令注册。")
        print(f"     你可以手动将 {WORM_SCRIPT} 加入 PATH。")
        return False


def setup_config():
    print("\n🔧 [2/2] 检查配置文件 ...")
    cfg_path = _user_config_path()
    example = _example_config_path()

    if cfg_path.is_file():
        print(f"  ✅ 配置文件已存在: {cfg_path}")
    else:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        if example.is_file():
            shutil.copy2(str(example), str(cfg_path))
            print(f"  ✅ 已从模板复制配置文件: {cfg_path}")
        else:
            cfg_path.write_text(_DEFAULT_TEMPLATE, encoding="utf-8")
            print(f"  ✅ 已生成默认配置文件: {cfg_path}")

    missing, unfilled = _check_config_fields(cfg_path)

    ok = True
    if missing:
        print(f"  ❌ 配置文件缺少字段: {', '.join(missing)}")
        ok = False
    if unfilled:
        print(f"  ⚠️  以下字段看起来还是占位符，请修改为真实值: {', '.join(unfilled)}")
        print(f"     编辑配置文件: {cfg_path}")
        ok = False

    if ok:
        print("  ✅ 配置文件字段完整")

    return ok, cfg_path


def cmd_setup(check_only=False):
    if check_only:
        print("\n🔍 worm 配置状态检查")
        print("=" * 40)
    else:
        print("\n🚀 worm 安装向导")
        print("=" * 40)

    issues = []

    if check_only:
        print("\n📌 全局命令:")
        sys_name = _system()
        if sys_name in ("linux", "darwin"):
            link = Path("/usr/local/bin/worm")
            if link.exists() or link.is_symlink():
                try:
                    real = link.resolve()
                except OSError:
                    real = None
                if real == WORM_SCRIPT:
                    print(f"  ✅ {link} → {WORM_SCRIPT}")
                else:
                    print(f"  ⚠️  {link} 存在但不指向当前脚本 (→ {real})")
                    issues.append("全局命令指向错误")
            else:
                print(f"  ❌ {link} 不存在")
                issues.append("全局命令未注册")
        elif sys_name == "windows":
            cmd_file = WORM_SCRIPT.parent / "worm.cmd"
            worm_dir = str(WORM_SCRIPT.parent)
            if cmd_file.exists():
                print(f"  ✅ 启动脚本: {cmd_file}")
            else:
                print(f"  ❌ 启动脚本不存在: {cmd_file}")
                issues.append("worm.cmd 未创建")
            if _dir_in_path(worm_dir):
                print(f"  ✅ PATH 已包含: {worm_dir}")
            else:
                print(f"  ❌ PATH 未包含: {worm_dir}")
                issues.append("PATH 未配置")
    else:
        if not setup_global_command():
            issues.append("全局命令注册未完成")

    if check_only:
        print("\n📌 配置文件:")
        cfg_path = _user_config_path()
        if cfg_path.is_file():
            print(f"  ✅ 存在: {cfg_path}")
            missing, unfilled = _check_config_fields(cfg_path)
            if missing:
                print(f"  ❌ 缺少字段: {', '.join(missing)}")
                issues.append("配置字段缺失")
            elif unfilled:
                print(f"  ⚠️  以下字段仍为占位符: {', '.join(unfilled)}")
                issues.append("配置字段未填写真实值")
            else:
                print("  ✅ 必填字段完整")
        else:
            found = find_config()
            if found:
                print(f"  ⚠️  首选路径不存在，但找到: {found}")
                missing_f, unfilled_f = _check_config_fields(found)
                if missing_f:
                    print(f"  ❌ 该文件缺少字段: {', '.join(missing_f)}")
                    issues.append("配置字段缺失")
                elif unfilled_f:
                    print(f"  ⚠️  以下字段仍为占位符: {', '.join(unfilled_f)}")
                    issues.append("配置字段未填写真实值")
                else:
                    print("  ✅ 必填字段完整")
            else:
                print("  ❌ 配置文件不存在")
                issues.append("配置文件未创建")
    else:
        ok, cfg_path = setup_config()
        if not ok:
            issues.append("配置文件未完善")

    print("\n" + "=" * 40)
    if not issues:
        print("🎉 一切就绪！你可以在任意终端使用: worm <文件> <邮箱>")
    else:
        print("📋 待完成事项:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n完成上述步骤后，再次运行 worm setup --check 检查。")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "setup":
        check_only = "--check" in sys.argv[2:]
        cmd_setup(check_only=check_only)
        sys.exit(0)

    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        sys.exit(0 if "-h" in sys.argv or "--help" in sys.argv else 1)

    filepath = sys.argv[1]
    recipient = sys.argv[2]

    if not os.path.exists(filepath):
        print(f"❌ 路径不存在: {filepath}")
        sys.exit(1)

    if not os.access(filepath, os.R_OK):
        print(f"❌ 没有读取权限: {filepath}")
        sys.exit(1)

    tmpdir = None
    is_dir = os.path.isdir(filepath)

    if "@" not in recipient:
        print(f"❌ 无效的邮箱地址: {recipient}")
        sys.exit(1)

    smtp_cfg = load_config()

    try:
        if is_dir:
            filepath, tmpdir = zip_directory(filepath)

        filesize = os.path.getsize(filepath)
        if filesize > MAX_ATTACH_SIZE:
            size_mb = filesize / 1024 / 1024
            limit_mb = MAX_ATTACH_SIZE / 1024 / 1024
            print(f"❌ 附件大小 {size_mb:.1f} MB 超过限制 ({limit_mb:.0f} MB)，邮箱可能拒收。")
            sys.exit(1)

        filename = os.path.basename(filepath)
        print(f"📤 正在发送 {filename} → {recipient} ...")

        msg = build_message(smtp_cfg, filepath, recipient)
        send(smtp_cfg, msg, recipient)
        print("✅ 发送成功！")
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP 认证失败，请检查邮箱账号和授权码。")
        sys.exit(1)
    except smtplib.SMTPException as exc:
        print(f"❌ SMTP 错误: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"❌ 发送失败: {exc}")
        sys.exit(1)
    finally:
        if tmpdir:
            cleanup_temp(tmpdir)


if __name__ == "__main__":
    main()