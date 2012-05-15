#!/bin/bash
ENABLED_SERVICES=n-vol
DEST=/opt/stack

function is_service_enabled() {
    services=$@
    for service in ${services}; do
        [[ ,${ENABLED_SERVICES}, =~ ,${service}, ]] && return 0
        [[ ${service} == "nova" && ${ENABLED_SERVICES} =~ "n-" ]] && return 0
        [[ ${service} == "glance" && ${ENABLED_SERVICES} =~ "g-" ]] && return 0
        [[ ${service} == "quantum" && ${ENABLED_SERVICES} =~ "q-" ]] && return 0
    done
    return 1
}

if is_service_enabled n-vol; then
    #
    # Configure a default volume group called 'nova-volumes' for the nova-volume
    # service if it does not yet exist.  If you don't wish to use a file backed
    # volume group, create your own volume group called 'nova-volumes' before
    # invoking stack.sh.
    #
    # By default, the backing file is 2G in size, and is stored in /opt/stack.
VOLUME_GROUP=${VOLUME_GROUP:-nova-volumes}
VOLUME_NAME_PREFIX=${VOLUME_NAME_PREFIX:-volume-}
    if ! sudo vgs $VOLUME_GROUP; then
        VOLUME_BACKING_FILE=${VOLUME_BACKING_FILE:-$DEST/nova-volumes-backing-file}
        VOLUME_BACKING_FILE_SIZE=${VOLUME_BACKING_FILE_SIZE:-2052M}
        # Only create if the file doesn't already exists
        [[ -f $VOLUME_BACKING_FILE ]] || truncate -s $VOLUME_BACKING_FILE_SIZE $VOLUME_BACKING_FILE
        DEV=`sudo losetup -f --show $VOLUME_BACKING_FILE`
        # Only create if the loopback device doesn't contain $VOLUME_GROUP
        if ! sudo vgs $VOLUME_GROUP; then sudo vgcreate $VOLUME_GROUP $DEV; fi
    fi

    if sudo vgs $VOLUME_GROUP; then
        # Remove nova iscsi targets
        sudo tgtadm --op show --mode target | grep $VOLUME_NAME_PREFIX | grep Target | cut -f3 -d ' ' | sudo xargs -n1 tgt-admin --delete || true
        # Clean out existing volumes
        for lv in `sudo lvs --noheadings -o lv_name $VOLUME_GROUP`; do
            # VOLUME_NAME_PREFIX prefixes the LVs we want
            if [[ "${lv#$VOLUME_NAME_PREFIX}" != "$lv" ]]; then
                sudo lvremove -f $VOLUME_GROUP/$lv
            fi
        done
    fi

    if [[ "$os_PACKAGE" = "deb" ]]; then
        # tgt in oneiric doesn't restart properly if tgtd isn't running
        # do it in two steps
        sudo stop tgt || true
        sudo start tgt
    else
        # bypass redirection to systemctl during restart
        #sudo /sbin/service --skip-redirect tgtd restart
      sudo /etc/init.d/tgtd restart
    fi
fi
