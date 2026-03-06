#!/usr/bin/env python3
"""
worm - 通过邮箱发送文件的命令行工具

用法: worm <文件或目录路径> <目标邮箱>
"""

import sys
import os
import smtplib
import configparser
import mimetypes
import shutil
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.encoders import encode_base64
from email.utils import formataddr, formatdate
from pathlib import Path


CONF_NAME = "worm.conf"
MAX_ATTACH_SIZE = 50 * 1024 * 1024


def find_config():
    candidates = [
        Path.home() / ".config" / "worm" / CONF_NAME,
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
        print(f"   1. ~/.config/worm/{CONF_NAME}")
        print(f"   2. ~/.{CONF_NAME}")
        print(f"   3. {Path(__file__).resolve().parent / CONF_NAME}")
        print(f"\n可从 worm.conf.example 复制并修改。")
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
    print(f"""
用法: {prog} <文件或目录路径> <目标邮箱>

示例:
  {prog} ./report.pdf zhangsan@qq.com
  {prog} ./project_dir zhangsan@qq.com
  {prog} /var/log/app.log admin@163.com

配置:
  首次使用前，复制 worm.conf.example 为 worm.conf，
  填写你的邮箱 SMTP 信息。配置文件搜索顺序：
    1. ~/.config/worm/worm.conf
    2. ~/.worm.conf
    3. 程序同目录/worm.conf
""")


def main():
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
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
        print(f"✅ 发送成功！")
    except smtplib.SMTPAuthenticationError:
        print(f"❌ SMTP 认证失败，请检查邮箱账号和授权码。")
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
