# EVPN All-Active ESI Handler

This handler is for Multihomed EVPN ESIs to manage the following scenarios to minimize traffic loss:
 - delay Multihomed ESI transition to UP on initial device boot;
 - handle core isolation scenarios (when all underlay or overlay BGP sessions goes down).

Only dualhomed interfaces are errdisbaled by the script while there are no established underlay and overlay BGP sessions towards network (to prevent clients to send traffic while the device isolated from the network).

## How it works

### Triggers
The handler is triggered by EOS on the following events:
 - during initial device boot (`on-boot`);
 - in case of BGP session state change by polling logs (`on-logging`).

### Script algorithm
The scipt is doing the following steps:
1.  Get list of established BGP EVPN sessions (using `show bgp evpn summary`).
2.  Get list of established underlay BGP IPv4 Unicast sessions (using `show bgp ipv4 unicast summary`).
3.  Get list of dualhomed ESIs/interfaces (using `show bgp evpn instance`).
    - For EOS prior 4.23.2 the script will revert back `show running-config` (because `show bgp evpn instance` has JSON output from EOS-4.23.2).
4.  Get list of dualhomed interfaces in errdisable state (using `show interfaces status` and list of interfaces from previous step).
5.  If no established BGP EVPN (overlay) or IPv4 (underlay) sessions the script will put dualhomed interfaces (from Step 3 above) to `errdisable` state (core isolation condition).
6.  If there is at least one BGP EVPN (overlay) session and at least one BGP IPv4 (underlay) session the script is resetting errdisabled interfaces (from Step 4 above) to `Up` state.
7.  Finish.

The script is not required any input parameters. All required information is collected by the script on startup by itself.

## Required EOS configuration
Enable EOS API:
```
!
management api http-commands
  protocol unix-socket
  no shutdown
!
```

Add event-handlers to trigger script:
```
!
event-handler handle_dualhomed_esi_on_bgp_down
  action bash /mnt/flash/scripts/evpn_esi_handler.py
  delay 0
  !
  trigger on-logging
    regex BGP-5-ADJCHANGE.*old state Established
!
event-handler handle_dualhomed_esi_on_bgp_up
  action bash /mnt/flash/scripts/evpn_esi_handler.py
  !
  trigger on-logging
    regex BGP-5-ADJCHANGE.*new state Established
!
event-handler handle_dualhomed_esi_on_boot
  trigger on-boot
  action bash /mnt/flash/scripts/evpn_esi_handler.py
  asynchronous
  timeout 600
!
```
