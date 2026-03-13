#!/usr/bin/env python3
"""
NPU Container Manager
昇腾 NPU Docker 容器管理工具
"""

import subprocess
import sys
import os
import json
from typing import List, Optional, Tuple, Dict
from pathlib import Path


class Config:
    """从 config.env 加载用户配置（敏感信息）"""

    def __init__(self, config_path: Optional[Path] = None):
        self.data: Dict[str, str] = {}
        if config_path is None:
            config_path = Path(__file__).parent / "config.env"
        if config_path.exists():
            self._load(config_path)

    def _load(self, path: Path):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                self.data[key.strip()] = value.strip()

    def get(self, key: str, default: str = "") -> str:
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        return bool(self.data.get(key))


class NPUContainerManager:
    """NPU容器管理器主类"""

    DEFAULT_IMAGE = "quay.io/ascend/cann:8.1.rc1-910b-ubuntu22.04-py3.10"
    SCRIPT_OUTPUT_DIR = Path.home() / "npu_container_scripts"
    DEFAULT_SHM_SIZE = "16g"

    ASCEND_IMAGE_KEYWORDS = [
        "ascend", "vllm", "cann", "mindspore", "mindie",
        "mindformers", "mindieservice", "npu", "atlas",
    ]

    REQUIRED_DEVICES = [
        "/dev/davinci_manager",
        "/dev/devmm_svm",
        "/dev/hisi_hdc",
    ]

    REQUIRED_VOLUMES = [
        "/usr/local/dcmi:/usr/local/dcmi",
        "/usr/local/bin/npu-smi:/usr/local/bin/npu-smi",
        "/usr/local/Ascend/driver:/usr/local/Ascend/driver",
        "/etc/ascend_install.info:/etc/ascend_install.info:ro",
        "/home/.cache:/root/.cache",
    ]

    def __init__(self):
        self.config = Config()
        self.SCRIPT_OUTPUT_DIR.mkdir(exist_ok=True)

    # ======================== 基础工具方法 ========================

    def run_command(self, cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """执行shell命令"""
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=False)
            stdout = result.stdout if result.stdout is not None else ""
            stderr = result.stderr if result.stderr is not None else ""
            return result.returncode, stdout, stderr
        except Exception as exc:
            return 1, "", str(exc)

    def confirm(self, prompt: str) -> bool:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        return answer == "y"

    def check_docker_available(self) -> bool:
        returncode, _, stderr = self.run_command(["docker", "version"])
        if returncode != 0:
            print(f"❌ Docker不可用: {stderr.strip()}")
            print("请确认Docker已安装、daemon已启动且当前用户有权限。")
            return False
        return True

    def is_ascend_image(self, image_name: str) -> bool:
        name_lower = image_name.lower()
        return any(kw in name_lower for kw in self.ASCEND_IMAGE_KEYWORDS)

    # ======================== 镜像相关 ========================

    def get_docker_images(self) -> List[str]:
        returncode, stdout, stderr = self.run_command(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
        )
        if returncode != 0:
            print(f"❌ 获取Docker镜像失败: {stderr}")
            return []
        return [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    def select_image(self) -> Optional[str]:
        images = self.get_docker_images()
        if not images:
            print("⚠️  未找到任何Docker镜像")
            return self.handle_no_image()

        ascend_images = [img for img in images if self.is_ascend_image(img)]
        other_images = [img for img in images if not self.is_ascend_image(img)]

        print("\n📦 当前可用的Docker镜像:")
        idx = 1
        if ascend_images:
            print("\n昇腾相关镜像:")
            for img in ascend_images:
                print(f"  {idx}. {img}")
                idx += 1
        if other_images:
            print("\n其他镜像:")
            for img in other_images:
                print(f"  {idx}. {img}")
                idx += 1

        all_images = ascend_images + other_images
        print(f"\n  0. 使用默认镜像 ({self.DEFAULT_IMAGE})")
        print("  q. 返回上级菜单")

        while True:
            choice = input("\n请选择镜像编号: ").strip()
            if choice.lower() == "q":
                return None
            if choice == "0":
                return self.handle_no_image()
            try:
                selected = int(choice)
                if 1 <= selected <= len(all_images):
                    return all_images[selected - 1]
                print(f"❌ 无效的编号，请输入 1-{len(all_images)} 或 0")
            except ValueError:
                print("❌ 请输入有效的数字")

    def handle_no_image(self) -> Optional[str]:
        print(f"\n💡 建议使用默认昇腾镜像: {self.DEFAULT_IMAGE}")
        if not self.confirm("是否拉取默认镜像?"):
            print("❌ 用户取消操作")
            return None
        return self.pull_image(self.DEFAULT_IMAGE)

    def pull_image(self, image: str) -> Optional[str]:
        print(f"\n🔄 正在拉取镜像: {image}")
        print("=" * 60)
        returncode, _, _ = self.run_command(["docker", "pull", image], capture_output=False)
        if returncode == 0:
            print("=" * 60)
            print(f"✅ 镜像拉取成功: {image}\n")
            return image
        print("❌ 镜像拉取失败")
        return None

    # ======================== NPU 检测与选择 ========================

    def detect_npus(self) -> int:
        npu_count = 0
        for i in range(8):
            if os.path.exists(f"/dev/davinci{i}"):
                npu_count += 1
        return npu_count

    def select_npus(self) -> Optional[List[int]]:
        npu_count = self.detect_npus()
        if npu_count == 0:
            print("❌ 未检测到可用的NPU设备")
            return None

        print(f"\n🎯 检测到 {npu_count} 张可用NPU (编号: 0-{npu_count-1})")
        print("\n使用说明:")
        print("  - 输入 '0' 使用0号卡")
        print("  - 输入 '0,1' 或 '01' 使用0号和1号卡")
        print("  - 输入 '0,1,2,3' 或 '0123' 使用0-3号卡")
        print("  - 输入 'q' 返回")

        while True:
            choice = input("\n请输入要使用的NPU编号: ").strip()
            if choice.lower() == "q":
                return None
            if not choice:
                print("❌ 请输入NPU编号")
                continue
            try:
                if "," in choice:
                    npu_ids = [int(x.strip()) for x in choice.split(",") if x.strip()]
                else:
                    npu_ids = [int(c) for c in choice]
                npu_ids = sorted(set(npu_ids))
                if all(0 <= npu_id < npu_count for npu_id in npu_ids):
                    print(f"✅ 已选择NPU: {npu_ids}")
                    return npu_ids
                print(f"❌ 无效的NPU编号，请输入 0-{npu_count-1} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")

    # ======================== 挂载与共享内存 ========================

    def select_volumes(self) -> List[str]:
        print("\n📁 配置额外的挂载目录")
        print("提示: 可以挂载模型目录、数据目录等")
        print("格式: 宿主机路径:容器路径[:选项] (例如: /data/models:/models 或 /data:/data:ro)")
        print("输入空行完成配置\n")

        volumes = []
        while True:
            volume = input("请输入挂载路径 (直接回车完成): ").strip()
            if not volume:
                break
            if ":" not in volume:
                print("❌ 格式错误，请使用 '宿主机路径:容器路径[:选项]' 格式")
                continue
            parts = volume.split(":")
            host_path = parts[0]
            if not os.path.exists(host_path):
                print(f"⚠️  警告: 宿主机路径不存在: {host_path}")
                if not self.confirm("是否仍要添加?"):
                    continue
            volumes.append(volume)
            print(f"✅ 已添加挂载: {volume}")
        return volumes

    def select_shm_size(self) -> str:
        print(f"\n💾 配置共享内存大小 (默认: {self.DEFAULT_SHM_SIZE})")
        choice = input(f"请输入共享内存大小 (直接回车使用默认值 {self.DEFAULT_SHM_SIZE}): ").strip()
        return choice if choice else self.DEFAULT_SHM_SIZE

    # ======================== Claude Code / Codex 可选集成 ========================

    def ask_enable_claude_codex(self) -> bool:
        """询问用户是否启用 Claude Code / Codex 支持"""
        print("\n🤖 可选: 启用 Claude Code / Codex 支持")
        print("  此选项会将 Node.js、Claude/Codex 配置挂载到容器内，")
        print("  并注入相关环境变量，方便在容器内使用 AI 编程助手。")
        print("  需要在 config.env 中配置相关 API Key。")
        return self.confirm("是否启用 Claude Code / Codex 支持?")

    def get_claude_codex_volumes(self) -> List[str]:
        """获取 Claude/Codex 相关挂载"""
        volumes = []
        nodejs_path = self.config.get("NODEJS_HOST_PATH")
        if nodejs_path and os.path.exists(nodejs_path):
            volumes.append(f"{nodejs_path}:/opt/nodejs")
        else:
            default_nodejs = Path.home() / "nodejs"
            if default_nodejs.exists():
                volumes.append(f"{default_nodejs}:/opt/nodejs")
            else:
                print("⚠️  未找到 Node.js 目录，Claude Code / Codex 可能无法正常使用")
                print("  请在 config.env 中设置 NODEJS_HOST_PATH 或将 Node.js 安装到 ~/nodejs")

        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            volumes.append(f"{claude_json}:/root/.claude.json")

        claude_dir = Path.home() / ".claude"
        if claude_dir.exists():
            volumes.append(f"{claude_dir}:/root/.claude")

        codex_dir = Path.home() / ".codex"
        if codex_dir.exists():
            volumes.append(f"{codex_dir}:/root/.codex")

        return volumes

    def get_claude_codex_env_vars(self) -> List[str]:
        """获取 Claude/Codex 相关环境变量"""
        env_vars = []
        env_vars.append(
            "PATH=/opt/nodejs/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        )

        if self.config.has("ANTHROPIC_BASE_URL"):
            env_vars.append(f"ANTHROPIC_BASE_URL={self.config.get('ANTHROPIC_BASE_URL')}")
        if self.config.has("ANTHROPIC_AUTH_TOKEN"):
            env_vars.append(f"ANTHROPIC_AUTH_TOKEN={self.config.get('ANTHROPIC_AUTH_TOKEN')}")
        if self.config.has("CODEX_API_KEY"):
            env_vars.append(f"CODEX_API_KEY={self.config.get('CODEX_API_KEY')}")

        return env_vars

    def ensure_claude_api_key_approved(self):
        """将 API Key 后20位写入 ~/.claude.json 的已批准列表"""
        api_key = self.config.get("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            return

        key_suffix = api_key[-20:]
        claude_json_path = Path.home() / ".claude.json"

        try:
            if claude_json_path.exists():
                data = json.loads(claude_json_path.read_text())
            else:
                data = {}

            approved = data.setdefault("customApiKeyResponses", {}).setdefault("approved", [])
            if key_suffix not in approved:
                approved.append(key_suffix)
                claude_json_path.write_text(json.dumps(data, indent=2))
                print("✅ 已将 API Key 后20位添加到 ~/.claude.json 批准列表")
        except Exception as exc:
            print(f"⚠️  更新 ~/.claude.json 失败: {exc}")

    def ensure_codex_config(self):
        """确保 codex 配置文件中包含容器内 /root 项目的信任设置"""
        codex_config_path = Path.home() / ".codex" / "config.toml"
        if not codex_config_path.exists():
            return

        try:
            content = codex_config_path.read_text()
            section = '[projects."/root"]'
            if section not in content:
                content += f"\n{section}\ntrust_level = \"trusted\"\n"
                codex_config_path.write_text(content)
                print("✅ 已将容器内 /root 项目添加到 codex 信任列表")
        except Exception as exc:
            print(f"⚠️  更新 codex 配置失败: {exc}")

    # ======================== 容器名称与冲突 ========================

    def generate_container_name(self, npu_ids: List[int]) -> str:
        npu_str = "_".join(map(str, npu_ids))
        return f"npu_{npu_str}"

    def container_exists(self, container_name: str) -> bool:
        returncode, stdout, _ = self.run_command(
            ["docker", "ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"]
        )
        if returncode != 0:
            return False
        return container_name in stdout.strip().split("\n")

    def handle_container_conflict(self, container_name: str) -> Optional[str]:
        print(f"\n⚠️  容器 '{container_name}' 已存在!")
        print("  1. 删除旧容器并重新创建")
        print("  2. 使用新名称 (自动追加后缀)")
        print("  3. 取消操作")

        while True:
            choice = input("\n请选择 (1/2/3): ").strip()
            if choice == "1":
                if not self.confirm(f"⚠️  确认删除旧容器 '{container_name}'?"):
                    print("❌ 已取消删除")
                    return None
                print(f"🗑️  正在删除旧容器 '{container_name}'...")
                returncode, _, stderr = self.run_command(["docker", "rm", "-f", container_name])
                if returncode != 0:
                    print(f"❌ 删除容器失败: {stderr}")
                    return None
                print("✅ 旧容器已删除")
                return container_name
            elif choice == "2":
                suffix = 1
                new_name = f"{container_name}_{suffix}"
                while self.container_exists(new_name):
                    suffix += 1
                    new_name = f"{container_name}_{suffix}"
                print(f"✅ 将使用新名称: {new_name}")
                return new_name
            elif choice == "3":
                return None
            else:
                print("❌ 请输入 1、2 或 3")

    # ======================== 脚本生成与容器创建 ========================

    def generate_script(
        self,
        image: str,
        npu_ids: List[int],
        extra_volumes: List[str],
        container_name: str,
        shm_size: str,
        enable_claude_codex: bool = False,
    ) -> Path:
        """生成容器启动脚本"""
        script_name = f"run_{container_name}.sh"
        script_path = self.SCRIPT_OUTPUT_DIR / script_name

        docker_args = [
            "docker run -d",
            f"  --name {container_name}",
            "  --restart unless-stopped",
            "  --network host",
            f"  --shm-size {shm_size}",
        ]

        for npu_id in npu_ids:
            docker_args.append(f"  --device /dev/davinci{npu_id}")

        for device in self.REQUIRED_DEVICES:
            docker_args.append(f"  --device {device}")

        ascend_devices = ",".join(map(str, npu_ids))
        docker_args.append(f"  -e ASCEND_VISIBLE_DEVICES={ascend_devices}")
        docker_args.append(f"  -e ASCEND_RT_VISIBLE_DEVICES={ascend_devices}")

        for volume in self.REQUIRED_VOLUMES:
            docker_args.append(f"  -v {volume}")

        for volume in extra_volumes:
            docker_args.append(f"  -v {volume}")

        if enable_claude_codex:
            for volume in self.get_claude_codex_volumes():
                docker_args.append(f"  -v {volume}")
            for env in self.get_claude_codex_env_vars():
                docker_args.append(f"  -e {env}")

        docker_args.append(f"  {image}")
        docker_args.append('  bash -c "while true; do sleep 3600; done"')

        script_content = "#!/bin/bash\n\n" + " \\\n".join(docker_args) + "\n"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        return script_path

    def create_container(self, script_path: Path) -> bool:
        print("\n🚀 正在创建容器...")
        print(f"📝 脚本路径: {script_path}")
        returncode, stdout, stderr = self.run_command(["bash", str(script_path)])
        if returncode == 0:
            container_id = stdout.strip()
            print("✅ 容器创建成功!")
            if container_id:
                print(f"📋 容器ID: {container_id[:12]}")
            return True
        print(f"❌ 容器创建失败: {stderr}")
        return False

    def show_usage_info(self, container_name: str):
        print(f"\n📖 使用说明:")
        print(f"  进入容器:   docker exec -it {container_name} bash")
        print(f"  查看日志:   docker logs {container_name}")
        print(f"  停止容器:   docker stop {container_name}")
        print(f"  启动容器:   docker start {container_name}")
        print(f"  删除容器:   docker rm -f {container_name}")

    # ======================== 容器管理 ========================

    def get_containers(self) -> List[Dict[str, str]]:
        returncode, stdout, stderr = self.run_command(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"]
        )
        if returncode != 0:
            print(f"❌ 获取容器列表失败: {stderr}")
            return []
        containers = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                containers.append({"name": parts[0], "status": parts[1], "image": parts[2]})
        return containers

    def select_container(self, containers: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        print("\n{:<4} {:<25} {:<35} {}".format("编号", "容器名", "状态", "镜像"))
        print("-" * 90)
        for idx, container in enumerate(containers, 1):
            print("{:<4} {:<25} {:<35} {}".format(
                idx, container["name"], container["status"], container["image"]
            ))
        print("\n  q. 返回")

        while True:
            choice = input("\n请选择容器编号: ").strip()
            if choice.lower() == "q":
                return None
            try:
                selected = int(choice)
                if 1 <= selected <= len(containers):
                    return containers[selected - 1]
                print(f"❌ 无效的编号，请输入 1-{len(containers)}")
            except ValueError:
                print("❌ 请输入有效的数字")

    def start_container(self, name: str):
        print(f"\n🔄 正在启动容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "start", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已启动")
        else:
            print(f"❌ 启动失败: {stderr}")

    def stop_container(self, name: str):
        print(f"\n🔄 正在停止容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "stop", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已停止")
        else:
            print(f"❌ 停止失败: {stderr}")

    def remove_container(self, name: str) -> bool:
        if not self.confirm(f"⚠️  确认删除容器 '{name}'?"):
            print("❌ 已取消")
            return False
        print(f"🗑️  正在删除容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "rm", "-f", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已删除")
            return True
        print(f"❌ 删除失败: {stderr}")
        return False

    def view_container_logs(self, name: str):
        print(f"\n📋 容器 '{name}' 最近日志:")
        print("-" * 60)
        self.run_command(["docker", "logs", "--tail", "50", name], capture_output=False)
        print("-" * 60)

    def get_container_volumes(self, name: str) -> List[Dict[str, str]]:
        returncode, stdout, stderr = self.run_command(
            ["docker", "inspect", "--format", "{{json .Mounts}}", name]
        )
        if returncode != 0:
            print(f"❌ 获取容器挂载信息失败: {stderr}")
            return []
        try:
            mounts = json.loads(stdout.strip())
        except json.JSONDecodeError:
            print("❌ 解析挂载信息失败")
            return []
        volumes = []
        for mount in mounts:
            if mount.get("Type") == "bind":
                volumes.append({
                    "source": mount.get("Source", ""),
                    "destination": mount.get("Destination", ""),
                    "mode": "ro" if not mount.get("RW", True) else "rw",
                })
        return volumes

    def manage_container_volumes(self, container: Dict[str, str]):
        name = container["name"]
        volumes = self.get_container_volumes(name)
        if volumes:
            print(f"\n📂 容器 '{name}' 当前已挂载的目录:")
            print("-" * 70)
            print("{:<4} {:<30} {:<30} {:<6}".format("编号", "宿主机路径", "容器内路径", "模式"))
            print("-" * 70)
            for idx, vol in enumerate(volumes, 1):
                print("{:<4} {:<30} {:<30} {:<6}".format(
                    idx, vol["source"], vol["destination"], vol["mode"]
                ))
            print("-" * 70)
        else:
            print(f"\n📂 容器 '{name}' 当前没有通过 -v 挂载的目录")

        print("\n是否需要添加新的挂载目录?")
        if not self.confirm("添加新挂载目录 (需要重建容器)"):
            return

        new_volumes = []
        print("\n📁 添加新的挂载目录")
        print("格式: 宿主机路径:容器路径[:选项] (例如: /data/models:/models)")
        print("输入空行完成配置\n")

        while True:
            volume = input("请输入挂载路径 (直接回车完成): ").strip()
            if not volume:
                break
            if ":" not in volume:
                print("❌ 格式错误")
                continue
            host_path = volume.split(":")[0]
            if not os.path.exists(host_path):
                print(f"⚠️  警告: 宿主机路径不存在: {host_path}")
                if not self.confirm("是否仍要添加?"):
                    continue
            new_volumes.append(volume)
            print(f"✅ 已添加挂载: {volume}")

        if not new_volumes:
            print("\n未添加任何新挂载目录")
            return

        print(f"\n📋 即将为容器 '{name}' 添加以下挂载:")
        for vol in new_volumes:
            print(f"  - {vol}")
        print("\n⚠️  此操作需要停止并重建容器 (数据不会丢失)")

        if not self.confirm("确认重建容器?"):
            print("❌ 已取消")
            return

        returncode, stdout, _ = self.run_command(
            ["docker", "inspect", "--format", "{{json .Config}}", name]
        )
        if returncode != 0:
            print("❌ 获取容器配置失败")
            return

        try:
            config = json.loads(stdout.strip())
        except json.JSONDecodeError:
            print("❌ 解析容器配置失败")
            return

        image = config.get("Image", container["image"])

        returncode, inspect_out, _ = self.run_command(
            ["docker", "inspect", "--format", "{{json .HostConfig}}", name]
        )
        host_config = json.loads(inspect_out.strip()) if returncode == 0 else {}

        existing_binds = host_config.get("Binds", []) or []

        def bind_dest(bind_str):
            parts = bind_str.split(":")
            return parts[1] if len(parts) >= 2 else bind_str

        required_dests = {bind_dest(v) for v in self.REQUIRED_VOLUMES}
        all_binds = list(self.REQUIRED_VOLUMES)
        for bind in existing_binds:
            if bind_dest(bind) not in required_dests:
                all_binds.append(bind)
                required_dests.add(bind_dest(bind))
        for bind in new_volumes:
            if bind_dest(bind) not in required_dests:
                all_binds.append(bind)
                required_dests.add(bind_dest(bind))

        existing_devices = host_config.get("Devices", []) or []
        shm_size = host_config.get("ShmSize", 0)
        shm_size_str = f"{shm_size // (1024**3)}g" if shm_size >= 1024**3 else self.DEFAULT_SHM_SIZE

        existing_env = config.get("Env", []) or []

        self.run_command(["docker", "rm", "-f", name])

        docker_cmd = [
            "docker", "run", "-d",
            "--name", name,
            "--restart", "unless-stopped",
            "--network", "host",
            "--shm-size", shm_size_str,
        ]

        for bind in all_binds:
            docker_cmd.extend(["-v", bind])

        for dev in existing_devices:
            path = dev.get("PathOnHost", "")
            if path:
                docker_cmd.extend(["--device", path])

        for env in existing_env:
            docker_cmd.extend(["-e", env])

        docker_cmd.append(image)
        docker_cmd.extend(["bash", "-c", "while true; do sleep 3600; done"])

        returncode, stdout, stderr = self.run_command(docker_cmd)
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已重建成功")
        else:
            print(f"❌ 重建容器失败: {stderr}")

    def show_container_actions(self, container: Dict[str, str]):
        name = container["name"]
        is_running = "Up" in container["status"]

        while True:
            print(f"\n📦 容器: {name}")
            print(f"   状态: {container['status']}")
            print(f"   镜像: {container['image']}")

            if is_running:
                print("\n  1. 进入容器 (exec)")
                print("  2. 停止容器")
                print("  3. 查看日志")
                print("  4. 删除容器")
                print("  5. 管理挂载目录")
                print("  q. 返回")
            else:
                print("\n  1. 启动容器")
                print("  2. 查看日志")
                print("  3. 删除容器")
                print("  4. 管理挂载目录")
                print("  q. 返回")

            choice = input("\n请选择: ").strip()
            if choice.lower() == "q":
                break

            if is_running:
                if choice == "1":
                    print(f"\n执行: docker exec -it {name} bash")
                    os.system(f"docker exec -it {name} bash")
                elif choice == "2":
                    self.stop_container(name)
                    container["status"] = "Exited"
                    is_running = False
                elif choice == "3":
                    self.view_container_logs(name)
                elif choice == "4":
                    if self.remove_container(name):
                        break
                elif choice == "5":
                    self.manage_container_volumes(container)
                    break
                else:
                    print("❌ 无效的选项")
            else:
                if choice == "1":
                    self.start_container(name)
                    break
                elif choice == "2":
                    self.view_container_logs(name)
                elif choice == "3":
                    if self.remove_container(name):
                        break
                elif choice == "4":
                    self.manage_container_volumes(container)
                    break
                else:
                    print("❌ 无效的选项")

    def manage_containers_menu(self):
        while True:
            containers = self.get_containers()
            if not containers:
                print("\n📭 当前没有任何容器")
                input("按回车返回主菜单...")
                return

            print(f"\n🐳 当前共有 {len(containers)} 个容器:")
            selected = self.select_container(containers)
            if selected is None:
                return
            self.show_container_actions(selected)

    # ======================== 创建容器流程 ========================

    def create_container_flow(self):
        while True:
            image = self.select_image()
            if image is None:
                return

            npu_ids = self.select_npus()
            if npu_ids is None:
                return

            extra_volumes = self.select_volumes()
            shm_size = self.select_shm_size()

            enable_claude_codex = self.ask_enable_claude_codex()
            if enable_claude_codex:
                self.ensure_claude_api_key_approved()
                self.ensure_codex_config()

            container_name = self.generate_container_name(npu_ids)
            if self.container_exists(container_name):
                container_name = self.handle_container_conflict(container_name)
                if container_name is None:
                    print("❌ 用户取消操作")
                    continue

            script_path = self.generate_script(
                image, npu_ids, extra_volumes, container_name, shm_size,
                enable_claude_codex=enable_claude_codex,
            )

            print(f"\n📋 配置摘要:")
            print(f"  镜像: {image}")
            print(f"  NPU: {npu_ids}")
            print(f"  容器名: {container_name}")
            print(f"  共享内存: {shm_size}")
            print(f"  额外挂载: {len(extra_volumes)} 个")
            print(f"  Claude/Codex: {'✅ 启用' if enable_claude_codex else '❌ 未启用'}")
            print(f"  脚本路径: {script_path}")

            if not self.confirm("\n确认创建容器?"):
                print("❌ 用户取消操作")
                continue

            if self.create_container(script_path):
                self.show_usage_info(container_name)

            if not self.confirm("是否创建另一个容器?"):
                break

    # ======================== 主菜单 ========================

    def run(self):
        print("=" * 60)
        print("🎮 NPU容器管理器")
        print("=" * 60)

        if not self.check_docker_available():
            sys.exit(1)

        while True:
            print("\n📌 主菜单:")
            print("  1. 创建新容器")
            print("  2. 管理已有容器")
            print("  q. 退出程序")

            choice = input("\n请选择: ").strip()

            if choice == "1":
                self.create_container_flow()
            elif choice == "2":
                self.manage_containers_menu()
            elif choice.lower() == "q":
                print("\n👋 退出程序")
                break
            else:
                print("❌ 无效的选项，请输入 1、2 或 q")


def main():
    try:
        manager = NPUContainerManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ 发生错误: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()