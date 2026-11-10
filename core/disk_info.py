"""
disk_info.py - Windows 디스크 정보 수집 모듈

PowerShell(Get-CimInstance Win32_DiskDrive)로 디스크 정보를 수집하고,
validator.py에서 사용할 딕셔너리 형태로 반환합니다.

※ Windows 업데이트로 wmic.exe가 제거되어 PowerShell 방식으로 교체했습니다.
   Win32_DiskDrive는 wmic diskdrive가 읽던 것과 같은 WMI 클래스라 값(MediaType 등)이 동일합니다.

반환 딕셔너리 구조:
    - disk_number (int): 디스크 번호
    - model (str): 디스크 모델명
    - media_type (str): 디스크 타입 (예: "Removable Media", "Fixed hard disk media")
    - has_volumes (bool): 파티션(볼륨) 존재 여부
    - size_bytes (int): 디스크 용량 (바이트)
"""

import json
import subprocess
import logging

logger = logging.getLogger(__name__)

# PowerShell 한 번 호출로 디스크 정보 + 파티션 개수를 함께 조회
#   Index      : 디스크 번호 (PHYSICALDRIVE 뒤의 숫자와 동일)
#   Partitions : 해당 디스크의 파티션 개수 (구 Win32_DiskDriveToDiskPartition 매핑 대체)
_PS_SCRIPT = (
    "try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}; "
    "$ErrorActionPreference = 'Stop'; "
    "@(Get-CimInstance -ClassName Win32_DiskDrive | "
    "Select-Object Index, DeviceID, Model, MediaType, Size, Partitions) | "
    "ConvertTo-Json -Compress"
)

# PyInstaller GUI 앱에서 콘솔 창이 깜빡이는 것 방지 (Windows 전용 플래그)
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _run_powershell(script: str, timeout: int = 20) -> str:
    """
    PowerShell 스크립트를 실행하고 stdout 문자열을 반환합니다.

    Raises:
        RuntimeError: 실행 실패 / 시간 초과 시
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        logger.error(f"PowerShell 시간 초과 ({timeout}초)")
        raise RuntimeError(f"PowerShell 시간 초과 ({timeout}초)")
    except OSError as e:
        logger.error(f"PowerShell 실행 불가: {e}")
        raise RuntimeError(f"PowerShell 실행 불가: {e}")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.error(f"PowerShell 명령 실패 (code={result.returncode}): {stderr}")
        raise RuntimeError(f"PowerShell 명령 실패: {stderr}")

    return result.stdout


def _build_disk_dict(raw: dict) -> dict | None:
    """
    Win32_DiskDrive 원본 데이터를 validator가 사용할 표준 딕셔너리로 변환합니다.

    Args:
        raw: PowerShell JSON에서 파싱한 디스크 1개 분량의 dict

    Returns:
        표준 디스크 정보 딕셔너리 또는 파싱 실패 시 None
    """
    # 디스크 번호: Index 우선, 없으면 DeviceID(\\.\PHYSICALDRIVE0)에서 추출
    disk_number = raw.get("Index")
    if disk_number is None:
        device_id = str(raw.get("DeviceID") or "")
        try:
            disk_number = int(device_id.upper().split("PHYSICALDRIVE")[-1])
        except (ValueError, IndexError):
            logger.warning(f"디스크 번호 파싱 실패: {device_id}")
            return None

    try:
        disk_number = int(disk_number)
    except (ValueError, TypeError):
        logger.warning(f"디스크 번호 변환 실패: {disk_number}")
        return None

    # 용량 (없으면 0) - 미디어 없는 카드리더는 Size가 null
    try:
        size_bytes = int(raw.get("Size") or 0)
    except (ValueError, TypeError):
        size_bytes = 0

    # 파티션 개수 (없으면 0)
    try:
        partitions = int(raw.get("Partitions") or 0)
    except (ValueError, TypeError):
        partitions = 0

    return {
        "disk_number": disk_number,
        "model": raw.get("Model") or "알 수 없음",
        "media_type": raw.get("MediaType") or "알 수 없음",
        "has_volumes": partitions > 0,
        "size_bytes": size_bytes,
    }


def get_all_disks() -> list[dict]:
    """
    시스템에 연결된 모든 물리 디스크 정보를 수집합니다.

    Returns:
        디스크 정보 딕셔너리 리스트. 각 항목은 다음 키를 포함:
            - disk_number (int)
            - model (str)
            - media_type (str)
            - has_volumes (bool)
            - size_bytes (int)

    Raises:
        RuntimeError: 디스크 정보 수집 실패 시.
            (볼륨 정보를 못 읽은 채로 진행하면 has_volumes가 잘못 False가 되어
             데이터가 있는 디스크를 포맷할 수 있으므로, 조용히 넘기지 않고 에러를 올립니다.)
    """
    output = _run_powershell(_PS_SCRIPT).strip()
    if not output:
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        logger.error(f"디스크 정보 JSON 파싱 실패: {e}\n{output[:500]}")
        raise RuntimeError(f"디스크 정보 파싱 실패: {e}")

    # 디스크가 1개면 리스트가 아니라 dict로 나오는 경우 대비
    if isinstance(data, dict):
        data = [data]

    disks = []
    for raw in data:
        parsed = _build_disk_dict(raw)
        if parsed is not None:
            disks.append(parsed)

    return disks


def get_disk_by_number(disk_number: int) -> dict | None:
    """
    특정 디스크 번호의 정보만 반환합니다.

    Args:
        disk_number: 조회할 디스크 번호

    Returns:
        디스크 정보 딕셔너리 또는 해당 디스크가 없으면 None
    """
    for disk in get_all_disks():
        if disk["disk_number"] == disk_number:
            return disk
    return None


def get_removable_disks() -> list[dict]:
    """
    이동식(Removable) 디스크만 필터링하여 반환합니다.

    Returns:
        Removable 타입 디스크 정보 리스트
    """
    return [d for d in get_all_disks() if "removable" in d["media_type"].lower()]
