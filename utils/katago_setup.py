"""Automated KataGo setup utility."""

import os
import sys
import platform
import urllib.request
import tarfile
import zipfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple


class KataGoSetup:
    """Automated KataGo download and setup."""

    # Latest KataGo version (update as needed)
    KATAGO_VERSION = "1.15.3"

    # Base URLs
    KATAGO_BASE_URL = "https://github.com/lightvector/KataGo/releases/download"
    NETWORK_BASE_URL = "https://media.githubusercontent.com/media/lightvector/KataGo/master/python/models"

    def __init__(self, install_dir: Optional[str] = None):
        """Initialize setup.

        Args:
            install_dir: Directory to install KataGo (default: ./katago_data)
        """
        if install_dir is None:
            install_dir = os.path.join(os.getcwd(), "katago_data")

        self.install_dir = Path(install_dir)
        self.install_dir.mkdir(exist_ok=True)

    def check_system_katago(self) -> Optional[Path]:
        """Check if KataGo is installed in system PATH.

        Returns:
            Path to system KataGo or None if not found
        """
        katago_path = shutil.which('katago')

        if katago_path:
            try:
                # Verify it works
                result = subprocess.run(
                    [katago_path, 'version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    print(f"Found system KataGo: {katago_path}")
                    # Extract version from output
                    for line in result.stdout.split('\n'):
                        if 'KataGo' in line:
                            print(f"Version: {line.strip()}")
                            break
                    return Path(katago_path)
            except Exception as e:
                print(f"Error checking system KataGo: {e}")

        return None

    def get_platform_info(self) -> Tuple[str, str]:
        """Get platform-specific download information.

        Returns:
            (platform_name, executable_name) tuple
        """
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                return "macos-arm64", "katago"
            else:
                return "macos-x64", "katago"
        elif system == "linux":
            return "linux-x64", "katago"
        elif system == "windows":
            return "windows-x64", "katago.exe"
        else:
            raise OSError(f"Unsupported platform: {system}")

    def download_file(self, url: str, dest_path: Path, description: str = "file") -> bool:
        """Download a file with progress indication.

        Args:
            url: URL to download
            dest_path: Destination path
            description: Description for progress messages

        Returns:
            True if successful
        """
        try:
            print(f"Downloading {description}...")
            print(f"URL: {url}")

            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, block_num * block_size * 100 / total_size)
                    print(f"\rProgress: {percent:.1f}%", end="", flush=True)

            urllib.request.urlretrieve(url, dest_path, progress_hook)
            print("\nDownload complete!")
            return True

        except Exception as e:
            print(f"\nError downloading {description}: {e}")
            return False

    def download_katago(self) -> Optional[Path]:
        """Download KataGo binary for current platform.

        Returns:
            Path to KataGo executable or None if failed
        """
        platform_name, exe_name = self.get_platform_info()

        # Construct download URL
        if platform_name == "macos-arm64":
            filename = f"katago-v{self.KATAGO_VERSION}-macos-arm64.zip"
        elif platform_name == "macos-x64":
            filename = f"katago-v{self.KATAGO_VERSION}-macos-x64.zip"
        elif platform_name == "linux-x64":
            filename = f"katago-v{self.KATAGO_VERSION}-linux-x64.zip"
        elif platform_name == "windows-x64":
            filename = f"katago-v{self.KATAGO_VERSION}-windows-x64.zip"
        else:
            print(f"No pre-built binary for platform: {platform_name}")
            return None

        url = f"{self.KATAGO_BASE_URL}/v{self.KATAGO_VERSION}/{filename}"
        archive_path = self.install_dir / filename

        # Download
        if not archive_path.exists():
            if not self.download_file(url, archive_path, f"KataGo {self.KATAGO_VERSION}"):
                return None
        else:
            print(f"KataGo archive already exists: {archive_path}")

        # Extract
        print("Extracting KataGo...")
        extract_dir = self.install_dir / "katago"
        extract_dir.mkdir(exist_ok=True)

        try:
            if filename.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif filename.endswith('.tar.gz'):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)

            # Find the katago executable
            exe_path = None
            for root, dirs, files in os.walk(extract_dir):
                if exe_name in files:
                    exe_path = Path(root) / exe_name
                    break

            if exe_path and exe_path.exists():
                # Make executable on Unix
                if platform.system() != "Windows":
                    os.chmod(exe_path, 0o755)

                print(f"KataGo executable: {exe_path}")
                return exe_path
            else:
                print(f"Could not find {exe_name} in extracted files")
                return None

        except Exception as e:
            print(f"Error extracting KataGo: {e}")
            return None

    def find_brew_networks(self) -> Optional[Path]:
        """Find neural networks installed by Homebrew.

        Returns:
            Path to a suitable network file or None
        """
        # Common homebrew paths
        brew_paths = [
            Path("/opt/homebrew/Cellar/katago"),
            Path("/usr/local/Cellar/katago"),
            Path("/home/linuxbrew/.linuxbrew/Cellar/katago")
        ]

        for brew_path in brew_paths:
            if not brew_path.exists():
                continue

            # Find network files
            for network_file in brew_path.rglob("*.bin.gz"):
                # Prefer b18 networks (good balance)
                if "b18" in network_file.name:
                    print(f"Found brew-installed network: {network_file}")
                    return network_file

            # If no b18, return any network
            for network_file in brew_path.rglob("*.bin.gz"):
                print(f"Found brew-installed network: {network_file}")
                return network_file

        return None

    def download_network(self, network_name: str = "b18c384nbt-s") -> Optional[Path]:
        """Download KataGo neural network.

        Args:
            network_name: Network identifier (default: b18c384nbt-s, balanced 18-block)

        Returns:
            Path to network file or None if failed
        """
        # First check for brew-installed networks
        brew_network = self.find_brew_networks()
        if brew_network:
            print("✓ Using brew-installed neural network")
            return brew_network

        # Use a specific known-good network file
        # You may need to update this URL based on what's actually available
        network_file = f"{network_name}7709731328-d1229425097.bin.gz"
        url = f"{self.NETWORK_BASE_URL}/{network_file}"

        network_path = self.install_dir / network_file

        if network_path.exists():
            print(f"Neural network already exists: {network_path}")
            return network_path

        # Try to download
        if self.download_file(url, network_path, f"neural network ({network_name})"):
            return network_path

        # If the specific URL doesn't work, provide instructions
        print("\nAutomatic network download failed.")
        print("Please download a neural network manually from:")
        print("https://github.com/lightvector/KataGo/releases")
        print(f"Save it to: {self.install_dir}")
        print("\nOr install KataGo via package manager:")
        print("  macOS: brew install katago")
        print("  Linux: Use your package manager")
        return None

    def generate_config(self, katago_path: Path, model_path: Path) -> Optional[Path]:
        """Generate KataGo configuration file.

        Args:
            katago_path: Path to KataGo executable
            model_path: Path to neural network model

        Returns:
            Path to config file or None if failed
        """
        config_path = self.install_dir / "katago_config.cfg"

        if config_path.exists():
            print(f"Config file already exists: {config_path}")
            return config_path

        try:
            print("Generating KataGo configuration...")

            # Run katago genconfig with auto mode
            result = subprocess.run(
                [
                    str(katago_path),
                    'genconfig',
                    'auto',
                    '-model', str(model_path),
                    '-output', str(config_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and config_path.exists():
                print(f"Config generated: {config_path}")
                return config_path
            else:
                print(f"Error generating config: {result.stderr}")
                # Try alternative method with stdin
                return self._generate_config_alternative(katago_path, model_path, config_path)

        except Exception as e:
            print(f"Error running katago genconfig: {e}")
            return self._generate_config_alternative(katago_path, model_path, config_path)

    def _generate_config_alternative(self, katago_path: Path, model_path: Path, config_path: Path) -> Optional[Path]:
        """Alternative config generation method.

        Args:
            katago_path: Path to KataGo executable
            model_path: Path to neural network model
            config_path: Path for output config

        Returns:
            Path to config file or None if failed
        """
        try:
            print("Trying alternative config generation method...")

            # Use genmove to test, then create a basic config manually
            # Or use benchmark command which doesn't need a config
            result = subprocess.run(
                [str(katago_path), 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            # Create a minimal config file manually
            basic_config = f"""# KataGo Configuration
# Auto-generated by Go Analysis Tool

logFile = katago.log
logAllGTPCommunication = false
logSearchInfo = false

numSearchThreads = 4
nnMaxBatchSize = 16
nnCacheSizePowerOfTwo = 20

maxVisits = 500
maxPlayouts = 300

# Rules
rules = tromp-taylor

# Model file
nnModelFile = {model_path}
"""

            with open(config_path, 'w') as f:
                f.write(basic_config)

            print(f"Created basic config: {config_path}")
            return config_path

        except Exception as e:
            print(f"Error creating alternative config: {e}")
            return None

    def setup(self) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """Run complete setup process.

        Returns:
            (katago_path, config_path, model_path) tuple or (None, None, None) if failed
        """
        print("=" * 60)
        print("KataGo Automated Setup")
        print("=" * 60)
        print()

        # Step 1: Check for system KataGo first (e.g., brew install)
        print("Step 1: Checking for system KataGo installation...")
        katago_path = self.check_system_katago()

        if not katago_path:
            print("System KataGo not found. Downloading KataGo binary...")
            katago_path = self.download_katago()
            if not katago_path:
                print("Failed to download KataGo")
                return None, None, None
        else:
            print("✓ Using system KataGo installation")
        print()

        # Step 2: Download neural network
        print("Step 2: Downloading neural network...")
        model_path = self.download_network()
        if not model_path:
            print("Failed to download neural network")
            print("\nPlease download manually:")
            print("1. Go to https://github.com/lightvector/KataGo/releases")
            print("2. Download a .bin.gz network file (e.g., b18c384nbt)")
            print(f"3. Save it to: {self.install_dir}")
            return katago_path, None, None
        print()

        # Step 3: Generate config
        print("Step 3: Generating configuration...")
        config_path = self.generate_config(katago_path, model_path)
        if not config_path:
            print("Failed to generate config")
            return katago_path, None, model_path
        print()

        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print(f"KataGo executable: {katago_path}")
        print(f"Neural network: {model_path}")
        print(f"Config file: {config_path}")
        print()

        return katago_path, config_path, model_path

    def verify_installation(self, katago_path: Path) -> bool:
        """Verify KataGo installation.

        Args:
            katago_path: Path to KataGo executable

        Returns:
            True if verification successful
        """
        try:
            print("Verifying KataGo installation...")
            result = subprocess.run(
                [str(katago_path), 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(f"KataGo version: {result.stdout.strip()}")
                return True
            else:
                print(f"Verification failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Error verifying installation: {e}")
            return False


def run_setup() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Run setup and return paths as strings.

    Returns:
        (katago_path, config_path, model_path) as strings
    """
    setup = KataGoSetup()
    katago_path, config_path, model_path = setup.setup()

    if katago_path and config_path and model_path:
        # Verify
        if setup.verify_installation(katago_path):
            return str(katago_path), str(config_path), str(model_path)

    return None, None, None


def quick_setup_system_katago() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Quick setup using system-installed KataGo (e.g., from brew).

    This function checks if KataGo is installed in the system PATH,
    downloads a neural network if needed, and generates a config file.

    Returns:
        (katago_path, config_path, model_path) as strings
    """
    setup = KataGoSetup()

    print("=" * 60)
    print("Quick Setup with System KataGo")
    print("=" * 60)
    print()

    # Check for system KataGo
    katago_path = setup.check_system_katago()
    if not katago_path:
        print("ERROR: KataGo not found in system PATH")
        print("Please install KataGo first:")
        print("  macOS: brew install katago")
        print("  Linux: Use your package manager or download from GitHub")
        return None, None, None

    # Download neural network
    print("\nDownloading neural network...")
    model_path = setup.download_network()
    if not model_path:
        return str(katago_path), None, None

    # Generate config
    print("\nGenerating configuration...")
    config_path = setup.generate_config(katago_path, model_path)
    if not config_path:
        return str(katago_path), None, str(model_path)

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"KataGo: {katago_path}")
    print(f"Neural network: {model_path}")
    print(f"Config: {config_path}")

    return str(katago_path), str(config_path), str(model_path)


if __name__ == "__main__":
    run_setup()
