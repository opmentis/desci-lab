#!/bin/bash

# Handle ramdisk setup
RAMDISK_PATH="/tmp/ramdisk"

# Check and cleanup existing ramdisk
if mountpoint -q "$RAMDISK_PATH"; then
    echo "Unmounting existing ramdisk..."
    sudo umount "$RAMDISK_PATH"
fi

# Create ramdisk directory if it doesn't exist
sudo mkdir -m 777 --parents "$RAMDISK_PATH"

# Mount new ramdisk based on OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo mount -t tmpfs -o size=10G ramdisk "$RAMDISK_PATH"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Check and detach existing disk
    EXISTING_DISK=$(df | grep ramdisk | awk '{print $1}')
    if [ ! -z "$EXISTING_DISK" ]; then
        diskutil unmount "$RAMDISK_PATH"
        diskutil eject "$EXISTING_DISK"
    fi
    diskutil erasevolume HFS+ "ramdisk" `hdiutil attach -nomount ram://2097152`
fi

# Create work directory
mkdir -p "$RAMDISK_PATH/work"