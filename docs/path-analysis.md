# Live topology and path analysis

The controller discovers switches and links in Mininet and saves them to
`tests/sample_data/topology_live.json`. The analyzer reads that topology and
calculates a route between two hosts.

## Start the controller

In one Ubuntu terminal:

    cd ~/network-diagnostic-tool
    ~/osken-venv/bin/osken-manager --observe-links src/path_analysis/controller.py

Leave it running.

## Start Mininet

In a second Ubuntu terminal:

    cd ~/network-diagnostic-tool
    sudo mn --topo linear,3 --controller=remote,ip=127.0.0.1,port=6633 --switch ovs,protocols=OpenFlow13

At the `mininet>` prompt, run `pingall`. The demonstrated run passed all six
connectivity checks with 0% packet loss.

## Calculate a route

In a terminal at the project folder:

    python3 -m src.path_analysis.analyzer tests/sample_data/topology_live.json host-18 host-218

Host IDs may change when Mininet restarts. Match the IDs in the live JSON to
the hosts' MAC addresses.

The demonstrated route was:

    host-18 -> switch-1 -> switch-2 -> switch-3 -> host-218

## Limitations

The controller assigns a placeholder latency of 1 ms per link and does not
provide bandwidth. Reported latency is an estimate, not a measurement;
bottleneck bandwidth is `null`.

`topology_live.json` is generated at runtime and ignored by Git. Share the
controller source and this guide with the team.
