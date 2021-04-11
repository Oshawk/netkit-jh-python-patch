NETKIT_HOME="$1"

# Read Netkit configuration
[ -f /etc/netkit.conf ] && . "/etc/netkit.conf"
[ -f "$1/netkit.conf" ] && . "$NETKIT_HOME/netkit.conf"
[ -f "$HOME/.netkit/netkit.conf" ] && . "$HOME/.netkit/netkit.conf"

# Assign default values to undefined parameters
: ${LOGFILENAME:=""}
: ${MCONSOLE_DIR:="$HOME/.netkit/mconsole"}
: ${HUB_SOCKET_DIR:="$HOME/.netkit/hubs"}
: ${HUB_SOCKET_PREFIX:="vhub"}
: ${HUB_SOCKET_EXTENSION:=".cnct"}
: ${HUB_LOG:="$HUB_SOCKET_DIR/vhubs.log"}
: ${VM_MEMORY:=32}
: ${VM_MEMORY_SKEW:=4}
: ${VM_MODEL_FS:="$NETKIT_HOME/fs/netkit-fs"}
: ${VM_KERNEL:="$NETKIT_HOME/kernel/netkit-kernel"}
: ${VM_CON0:=xterm}
: ${VM_CON1:=none}
: ${CON0_PORTHELPER:="no"}
: ${TERM_TYPE:=xterm}
: ${MAX_INTERFACES:=40}
: ${MIN_MEM:=12}
: ${MAX_MEM:=512}
: ${MAX_SIMULTANEOUS_VMS:=5}
: ${GRACE_TIME:=0}
: ${USE_SUDO:="yes"}
: ${TMUX_OPEN_TERMS:="no"}
: ${CHECK_FOR_UPDATES:="yes"}
: ${UPDATE_CHECK_PERIOD:=5}

# Check whether some environment variables override default settings
[ ! -z "$NETKIT_FILESYSTEM" ] && VM_MODEL_FS=$NETKIT_FILESYSTEM
[ ! -z "$NETKIT_MEMORY" ] && VM_MEMORY=$NETKIT_MEMORY
[ ! -z "$NETKIT_KERNEL" ] && VM_KERNEL=$NETKIT_KERNEL
[ ! -z "$NETKIT_CON0" ] && VM_CON0=$NETKIT_CON0
[ ! -z "$NETKIT_CON1" ] && VM_CON1=$NETKIT_CON1
[ ! -z "$NETKIT_TERM" ] && TERM_TYPE=$NETKIT_TERM

# Print all the variables for processing in python.
echo -n "LOGFILENAME "
echo "$LOGFILENAME" | base64
echo -n "MCONSOLE_DIR "
echo "$MCONSOLE_DIR" | base64
echo -n "HUB_SOCKET_DIR "
echo "$HUB_SOCKET_DIR" | base64
echo -n "HUB_SOCKET_PREFIX "
echo "$HUB_SOCKET_PREFIX" | base64
echo -n "HUB_SOCKET_EXTENSION "
echo "$HUB_SOCKET_EXTENSION" | base64
echo -n "HUB_LOG "
echo "$HUB_LOG" | base64
echo -n "VM_MEMORY "
echo "$VM_MEMORY" | base64
echo -n "VM_MEMORY_SKEW "
echo "$VM_MEMORY_SKEW" | base64
echo -n "VM_MODEL_FS "
echo "$VM_MODEL_FS" | base64
echo -n "VM_KERNEL "
echo "$VM_KERNEL" | base64
echo -n "VM_CON0 "
echo "$VM_CON0" | base64
echo -n "VM_CON1 "
echo "$VM_CON1" | base64
echo -n "CON0_PORTHELPER "
echo "$CON0_PORTHELPER" | base64
echo -n "TERM_TYPE "
echo "$TERM_TYPE" | base64
echo -n "MAX_INTERFACES "
echo "$MAX_INTERFACES" | base64
echo -n "MIN_MEM "
echo "$MIN_MEM" | base64
echo -n "MAX_MEM "
echo "$MAX_MEM" | base64
echo -n "MAX_SIMULTANEOUS_VMS "
echo "$MAX_SIMULTANEOUS_VMS" | base64
echo -n "GRACE_TIME "
echo "$GRACE_TIME" | base64
echo -n "USE_SUDO "
echo "$USE_SUDO" | base64
echo -n "TMUX_OPEN_TERMS "
echo "$TMUX_OPEN_TERMS" | base64
echo -n "CHECK_FOR_UPDATES "
echo "$CHECK_FOR_UPDATES" | base64
echo -n "UPDATE_CHECK_PERIOD "
echo "$UPDATE_CHECK_PERIOD" | base64
