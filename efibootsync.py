#!/usr/bin/env python3.7
"""
Syncs systemd-boot configuration to efi boot variables so the EFI boot can bypass systemd-boot
"""
import json
import os
import re
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
    Get mounted directories and associated information

    Returns:

    """
    try:
        sts, stdout = run("lsblk -J --output=MOUNTPOINT,LABEL,NAME,PKNAME,KNAME")
    except Exception as e:
        print(e)
        return
    h = {}
    for bd in json.loads(stdout).get("blockdevices"):
        for mp in bd.get("children"):
            mountpoint = mp.get("mountpoint") if mp else None
            if not mountpoint:
                continue
            partition = mp.get('kname')
            label = mp.get("label")
            device = mp.get("pkname")
            h[mountpoint] = {'partition': partition, 'device': device, 'label': label, 'mountpoint': mountpoint}
    return h


def main() -> None:
    """
    Do It.

    Returns:

    """
    h = get_mounts()
    boot_mount = h.get("/boot") or h.get('/efi')
    boot_directory = boot_mount['mountpoint']
    boot_partition = boot_mount['partition']
    boot_device = boot_mount['device']
    part_number = re.sub('[^0-9]', '', boot_partition.replace(boot_device, ''))
    if not boot_mount:
        print("Cannot determine boot mount")
        os._exit(-1)
    default = None
    for line in open(f"{boot_directory}/loader/loader.conf"):
        try:
            command, value = split_and_strip(line)
            if command == "default":
                default = value.strip()
        except:
            pass
    print(f"Default={default}")
    new_boot_entries = []
    with os.scandir(f'{boot_directory}/loader/entries') as it:
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
                        if command in ("linux", "efi"):
                            efistub = value
                        elif command == "initrd":
                            initrds.append(value)
                        elif command == "title":
                            title = " ".join(a[1:])
                        elif command == "options":
                            initrd_options = " ".join(a[1:])
                    except Exception as e:
                        print(f"ERROR {e}", line)
                new_boot_entries.append(dict(default=entry.name.replace(".conf", "") == default,
                                             title=title,
                                             efistub=efistub,
                                             initrds=initrds,
                                             options=initrd_options))
                if not default:
                    default = title
        new_boot_entries.sort(key=lambda x: x.get("title").lower())
        # for e in new_boot_entries:
        #     print(e)
        status_code, s = run('efibootmgr')
        if status_code:
            print("Error getting current boot entries")
            os._exit(-1)
        boot_entries = {}
        boot_labels = {}
        for line in s.split('\n'):
            try:
                entry, label = line.split(maxsplit=1)
            except:
                continue
            if ':' in entry:
                continue
            entry_id = entry.replace('Boot', '').replace('*', '')
            boot_entries[entry_id] = label
            boot_labels[label] = entry_id
        for nbe in new_boot_entries:
            title = nbe["title"]
            efistub = nbe['efistub']
            options = nbe['options']
            initrds = nbe['initrds']
            initrd = " ".join([f"initrd={s}" for s in initrds]).strip()
            existing_label = boot_labels.get(title)
            if existing_label:
                print(f"Label exists {title}", existing_label)
                c = f"""sudo efibootmgr --delete-bootnum -b {existing_label}"""
                run(c)
            create = "--create" if nbe.get("default") else "--create-only"
            c = f"""sudo efibootmgr --disk /dev/{boot_device} --part {part_number} {create} --label "{title}" --loader {efistub} --unicode '{options} {initrd}' --verbose"""
            print(c)
            run(c)


if __name__ == '__main__':
    main()
