#!/usr/bin/env python3
"""
NPU容器管理器
用于管理昇腾NPU的Docker容器创建和配置
"""

import subprocess
import sys
import os
from typing import List, Optional, Tuple, Dict
from pathlib import Path


class NPUContainerManager:
    """NPU容器管理器主类"""

    DEFAULT_IMAGE = "quay.io/ascend/vllm-ascend:main"
    SCRIPT_OUTPUT_DIR = Path.home() / "npu_container_scripts"
    DEFAULT_SHM_SIZE = "16g"

    ASCEND_IMAGE_KEYWORDS = [
        "ascend", "vllm", "cann", "mindspore", "mindie",
        "mindformers", "mindieservice", "npu", "atlas",
    ]

    REQUIRED_DEVICES = [
        "/dev/davinci_manager",
        "/dev/devmm_svm",
        "/dev/hisi_hdc"
    ]

    REQUIRED_VOLUMES = [
        "/usr/local/dcmi:/usr/local/dcmi",
        "/usr/local/bin/npu-smi:/usr/local/bin/npu-smi",
        "/usr/local/Ascend/driver:/usr/local/Ascend/driver",
        "/etc/ascend_install.info:/etc/ascend_install.info:ro",
        "/home/.cache:/root/.cache"
    ]

    def __init__(self):
        self.SCRIPT_OUTPUT_DIR.mkdir(exist_ok=True)

    # ======================== 基础工具方法 ========================

    def run_command(self, cmd: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """执行shell命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False
            )
            stdout = result.stdout if result.stdout is not None else ""
            stderr = result.stderr if result.stderr is not None else ""
            return result.returncode, stdout, stderr
        except Exception as e:
            return 1, "", str(e)

    def confirm(self, prompt: str) -> bool:
        """二次确认"""
        answer = input(f"{prompt} (y/n): ").strip().lower()
        return answer == "y"

    def check_docker_available(self) -> bool:
        """检查Docker是否可用"""
        returncode, _, stderr = self.run_command(["docker", "version"])
        if returncode != 0:
            print(f"❌ Docker不可用: {stderr.strip()}")
            print("请确认Docker已安装、daemon已启动且当前用户有权限。")
            return False
        return True

    def is_ascend_image(self, image_name: str) -> bool:
        """判断是否为昇腾相关镜像"""
        name_lower = image_name.lower()
        return any(kw in name_lower for kw in self.ASCEND_IMAGE_KEYWORDS)

    # ======================== 镜像相关 ========================

    def get_docker_images(self) -> List[str]:
        """获取当前Docker镜像列表"""
        returncode, stdout, stderr = self.run_command(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
        )
        if returncode != 0:
            print(f"❌ 获取Docker镜像失败: {stderr}")
            return []
        return [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    def select_image(self) -> Optional[str]:
        """让用户选择镜像"""
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
                else:
                    print(f"❌ 无效的编号，请输入 1-{len(all_images)} 或 0")
            except ValueError:
                print("❌ 请输入有效的数字")

    def handle_no_image(self) -> Optional[str]:
        """处理没有合适镜像的情况"""
        print(f"\n💡 建议使用默认昇腾镜像: {self.DEFAULT_IMAGE}")
        if not self.confirm("是否拉取默认镜像?"):
            print("❌ 用户取消操作")
            return None
        return self.pull_image(self.DEFAULT_IMAGE)

    def pull_image(self, image: str) -> Optional[str]:
        """拉取Docker镜像"""
        print(f"\n🔄 正在拉取镜像: {image}")
        print("=" * 60)

        returncode, _, _ = self.run_command(["docker", "pull", image], capture_output=False)

        if returncode == 0:
            print("=" * 60)
            print(f"✅ 镜像拉取成功: {image}\n")
            return image
        else:
            print("❌ 镜像拉取失败")
            return None

    # ======================== NPU 检测与选择 ========================

    def detect_npus(self) -> int:
        """检测可用的NPU数量"""
        npu_count = 0
        for i in range(8):
            if os.path.exists(f"/dev/davinci{i}"):
                npu_count += 1
        return npu_count

    def select_npus(self) -> Optional[List[int]]:
        """让用户选择要使用的NPU"""
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
                else:
                    print(f"❌ 无效的NPU编号，请输入 0-{npu_count-1} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")

    # ======================== 挂载与共享内存 ========================

    def select_volumes(self) -> List[str]:
        """让用户选择额外的挂载目录"""
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
        """让用户配置共享内存大小"""
        print(f"\n💾 配置共享内存大小 (默认: {self.DEFAULT_SHM_SIZE})")
        choice = input(f"请输入共享内存大小 (直接回车使用默认值 {self.DEFAULT_SHM_SIZE}): ").strip()
        if not choice:
            return self.DEFAULT_SHM_SIZE
        return choice

    # ======================== 容器名称与冲突 ========================

    def generate_container_name(self, npu_ids: List[int]) -> str:
        """根据NPU编号生成容器名称"""
        npu_str = "_".join(map(str, npu_ids))
        return f"npu_{npu_str}"

    def container_exists(self, container_name: str) -> bool:
        """检测容器名是否已存在"""
        returncode, stdout, _ = self.run_command(
            ["docker", "ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"]
        )
        if returncode != 0:
            return False
        return container_name in stdout.strip().split("\n")

    def handle_container_conflict(self, container_name: str) -> Optional[str]:
        """处理容器名冲突"""
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

    def generate_script(self, image: str, npu_ids: List[int], extra_volumes: List[str],
                        container_name: str, shm_size: str) -> Path:
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

        docker_args.append(f"  {image}")
        docker_args.append("  bash -c \"while true; do sleep 3600; done\"")

        script_content = "#!/bin/bash\n\n" + " \\\n".join(docker_args) + "\n"

        script_path.write_text(script_content)
        script_path.chmod(0o755)

        return script_path

    def create_container(self, script_path: Path) -> bool:
        """执行脚本创建容器"""
        print("\n🚀 正在创建容器...")
        print(f"📝 脚本路径: {script_path}")

        returncode, stdout, stderr = self.run_command(["bash", str(script_path)])

        if returncode == 0:
            container_id = stdout.strip()
            print("✅ 容器创建成功!")
            if container_id:
                print(f"   容器ID: {container_id[:12]}")
            return True
        else:
            print(f"❌ 容器创建失败: {stderr}")
            return False

    def show_usage_info(self, container_name: str):
        """显示容器使用说明"""
        print("\n" + "=" * 60)
        print("📖 容器使用说明")
        print("=" * 60)
        print(f"\n进入容器:")
        print(f"  docker exec -it {container_name} bash")
        print(f"\n查看容器状态:")
        print(f"  docker ps -a | grep {container_name}")
        print(f"\n停止容器:")
        print(f"  docker stop {container_name}")
        print(f"\n启动容器:")
        print(f"  docker start {container_name}")
        print(f"\n删除容器:")
        print(f"  docker rm -f {container_name}")
        print("\n" + "=" * 60 + "\n")

    # ======================== 容器管理功能 ========================

    def get_containers(self) -> List[Dict[str, str]]:
        """获取所有容器信息"""
        fmt = "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.ID}}"
        returncode, stdout, stderr = self.run_command(
            ["docker", "ps", "-a", "--format", fmt]
        )
        if returncode != 0:
            print(f"❌ 获取容器列表失败: {stderr}")
            return []

        containers = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                containers.append({
                    "name": parts[0],
                    "image": parts[1],
                    "status": parts[2],
                    "id": parts[3][:12],
                })
        return containers

    def select_container(self, containers: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """让用户选择一个容器"""
        header = "\n{:<4} {:<25} {:<35} {:<20} {:<14}".format(
            "编号", "容器名", "镜像", "状态", "ID"
        )
        print(header)
        print("-" * 100)
        for idx, ctn in enumerate(containers, 1):
            row = "{:<4} {:<25} {:<35} {:<20} {:<14}".format(
                idx, ctn["name"], ctn["image"], ctn["status"], ctn["id"]
            )
            print(row)

        print("\n  q. 返回上级菜单")

        while True:
            choice = input("\n请选择容器编号: ").strip()
            if choice.lower() == "q":
                return None
            try:
                selected = int(choice)
                if 1 <= selected <= len(containers):
                    return containers[selected - 1]
                else:
                    print(f"❌ 无效的编号，请输入 1-{len(containers)}")
            except ValueError:
                print("❌ 请输入有效的数字")

    def show_container_actions(self, container: Dict[str, str]):
        """显示并执行容器操作菜单"""
        name = container["name"]
        status = container["status"]
        is_running = status.lower().startswith("up")

        while True:
            print(f"\n📦 容器: {name}")
            print(f"   状态: {status}")
            print(f"   镜像: {container['image']}")
            print(f"   ID:   {container['id']}")
            print("\n可用操作:")
            if is_running:
                print("  1. 停止容器")
                print("  2. 重启容器")
                print("  3. 进入容器 (exec bash)")
                print("  4. 查看日志")
                print("  5. 删除容器 (强制)")
            else:
                print("  1. 启动容器")
                print("  2. 查看日志")
                print("  3. 删除容器")
            print("  q. 返回容器列表")

            choice = input("\n请选择操作: ").strip()

            if choice.lower() == "q":
                break

            if is_running:
                if choice == "1":
                    self.stop_container(name)
                    break
                elif choice == "2":
                    self.restart_container(name)
                    break
                elif choice == "3":
                    self.exec_container(name)
                    break
                elif choice == "4":
                    self.view_container_logs(name)
                elif choice == "5":
                    if self.remove_container(name):
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
                else:
                    print("❌ 无效的选项")

    def stop_container(self, name: str):
        """停止容器"""
        if not self.confirm(f"⚠️  确认停止容器 '{name}'?"):
            print("❌ 已取消")
            return
        print(f"⏳ 正在停止容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "stop", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已停止")
        else:
            print(f"❌ 停止失败: {stderr}")

    def start_container(self, name: str):
        """启动容器"""
        if not self.confirm(f"确认启动容器 '{name}'?"):
            print("❌ 已取消")
            return
        print(f"⏳ 正在启动容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "start", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已启动")
        else:
            print(f"❌ 启动失败: {stderr}")

    def restart_container(self, name: str):
        """重启容器"""
        if not self.confirm(f"⚠️  确认重启容器 '{name}'?"):
            print("❌ 已取消")
            return
        print(f"⏳ 正在重启容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "restart", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已重启")
        else:
            print(f"❌ 重启失败: {stderr}")

    def remove_container(self, name: str) -> bool:
        """删除容器"""
        if not self.confirm(f"⚠️  确认删除容器 '{name}'? 此操作不可恢复"):
            print("❌ 已取消")
            return False
        if not self.confirm(f"⚠️⚠️ 再次确认: 真的要删除容器 '{name}' 吗?"):
            print("❌ 已取消")
            return False
        print(f"🗑️  正在删除容器 '{name}'...")
        returncode, _, stderr = self.run_command(["docker", "rm", "-f", name])
        if returncode == 0:
            print(f"✅ 容器 '{name}' 已删除")
            return True
        else:
            print(f"❌ 删除失败: {stderr}")
            return False

    def exec_container(self, name: str):
        """进入容器"""
        if not self.confirm(f"确认进入容器 '{name}'?"):
            print("❌ 已取消")
            return
        print(f"\n🔗 正在进入容器 '{name}'...")
        print("提示: 输入 'exit' 退出容器\n")
        subprocess.run(["docker", "exec", "-it", name, "bash"], check=False)
        print(f"\n📤 已退出容器 '{name}'")

    def view_container_logs(self, name: str):
        """查看容器日志"""
        if not self.confirm(f"查看容器 '{name}' 的最近 50 行日志?"):
            print("❌ 已取消")
            return
        print(f"\n📋 容器 '{name}' 的日志 (最近50行):")
        print("-" * 60)
        returncode, stdout, stderr = self.run_command(
            ["docker", "logs", "--tail", "50", name]
        )
        if returncode == 0:
            print(stdout if stdout.strip() else "(日志为空)")
        else:
            print(f"❌ 获取日志失败: {stderr}")
        print("-" * 60)

    def manage_containers_menu(self):
        """容器管理主菜单"""
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
        """创建容器的完整交互流程"""
        while True:
            image = self.select_image()
            if image is None:
                return

            npu_ids = self.select_npus()
            if npu_ids is None:
                return

            extra_volumes = self.select_volumes()

            shm_size = self.select_shm_size()

            container_name = self.generate_container_name(npu_ids)
            if self.container_exists(container_name):
                container_name = self.handle_container_conflict(container_name)
                if container_name is None:
                    print("❌ 用户取消操作")
                    continue

            script_path = self.generate_script(
                image, npu_ids, extra_volumes, container_name, shm_size
            )

            print(f"\n📋 配置摘要:")
            print(f"  镜像: {image}")
            print(f"  NPU: {npu_ids}")
            print(f"  容器名: {container_name}")
            print(f"  共享内存: {shm_size}")
            print(f"  额外挂载: {len(extra_volumes)} 个")
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
        """主运行流程"""
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
    """程序入口"""
    try:
        manager = NPUContainerManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
