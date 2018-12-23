#!/usr/bin/env python3.7
"""
Syncs systemd-boot configuration to efi boot variables so the EFI boot can bypass systemd-boot
"""
import json
import os
import shlex
import subprocess
from typing import List


def split_and_strip(s: str) -> List[str]:
    """
    Splits the provided string and returns an array where each substring is stripped
    Args:
        s ():

    Returns:

    """
    if not s:
        return []
    return [s1.strip() for s1 in s.split()]


def run(cmd: str):
    """
    Run the specified command (using the shell for globbing/path search.)

    Args:
        cmd (str): Command to execute

    Returns:
        Tuple[int, str]: exit status, command stdout/stderr
    """
    try:
        s = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        return 0, s.decode('utf-8')
    except subprocess.CalledProcessError as ce:
        print(f"Error {ce} executing {cmd}")
        return ce.returncode, str(ce)
    except Exception as e:
        print(f"Exception {e} executing {cmd}")
        return -1, str(e)


def get_mounts():
    """
    Get mounted directories.

    Returns:

    """
    try:
        sts, stdout = run("lsblk -J --output=MOUNTPOINT,LABEL,NAME")
    except Exception as e:
        print(e)
        return
    h = {}
    for bd in json.loads(stdout).get("blockdevices"):
        for mp in bd.get("children"):
            mountpoint = mp.get("mountpoint") if mp else None
            if not mountpoint:
                continue
            device = mp.get('name')
            label = mp.get("label")
            h[mountpoint] = {'device': device, 'label': label}
    return h


def main() -> None:
    """
    Do It.

    Returns:

    """
    default = None
    for line in open("/boot/loader/loader.conf"):
        try:
            command, value = split_and_strip(line)
            if command == "default":
                default = value.strip()
        except:
            pass
    print(f"Default={default}")
    print(get_mounts())
    with os.scandir('/boot/loader/entries') as it:
        for entry in it:
            if entry.name.endswith('.conf') and entry.is_file():
                title = entry.name
                initrds = []
                initrd_options = None
                efistub = None
                for line in open(os.path.join('/boot/loader/entries', entry.name)):
                    try:
                        a = split_and_strip(line)
                        if len(a) < 2 or a[0].startswith('#'):
                            continue
                        command = a[0]
                        value = a[1]
                        # print(f"\t\t{command} {value}")
                        if command in ("linux", "efi"):
                            efistub = value
                        elif command == "initrd":
                            initrds.append(value)
                        elif command == "title":
                            title = value
                        elif command == "options":
                            initrd_options = " ".join(a[2:])
                    except Exception as e:
                        print(f"ERROR {e}", line)
                print(f"\ttitle={title}")
                print(f"\t\tefistub={efistub}")
                print(f"\t\tinitrd {' initrd='.join(initrds)}")
                print(f"\t\toptions={initrd_options}")
                print(" ")
                # bootstr =
        print(run('efibootmgr'))

if __name__ == '__main__':
    main()
