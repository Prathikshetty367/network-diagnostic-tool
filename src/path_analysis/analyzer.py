import heapq
import json
import sys


def analyze(topology, source, destination):
    nodes = {node["id"] for node in topology["nodes"]}
    if source not in nodes or destination not in nodes:
        raise ValueError("Source or destination is not in the topology")

    graph = {node_id: [] for node_id in nodes}

    for link in topology["links"]:
        if link.get("status", "up") != "up":
            continue

        start = link["source"]
        end = link["target"]
        latency = float(link.get("latency_ms", 1))

        graph[start].append((end, latency, link))
        if not link.get("directed", False):
            graph[end].append((start, latency, link))

    distances = {source: 0}
    previous = {}
    queue = [(0, source)]

    while queue:
        distance, current = heapq.heappop(queue)
        if distance > distances.get(current, float("inf")):
            continue
        if current == destination:
            break

        for neighbor, latency, link in graph[current]:
            new_distance = distance + latency
            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                previous[neighbor] = (current, link)
                heapq.heappush(queue, (new_distance, neighbor))

    if destination not in distances:
        raise ValueError(f"No available path from {source} to {destination}")

    path = [destination]
    links_used = []
    current = destination
    while current != source:
        parent, link = previous[current]
        path.append(parent)
        links_used.append(link)
        current = parent

    path.reverse()
    links_used.reverse()

    bandwidths = [
        link["bandwidth_mbps"]
        for link in links_used
        if "bandwidth_mbps" in link
    ]

    return {
        "source": source,
        "destination": destination,
        "path": path,
        "hops": path[1:-1],
        "path_characteristics": {
            "hop_count": len(links_used),
            "total_latency_ms": round(distances[destination], 3),
            "bottleneck_bandwidth_mbps": min(bandwidths) if bandwidths else None,
        },
    }


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 -m src.path_analysis.analyzer "
            "<topology.json> <source> <destination>"
        )
        sys.exit(1)

    topology_file, source, destination = sys.argv[1:]

    try:
        with open(topology_file, encoding="utf-8") as file:
            topology = json.load(file)
        result = analyze(topology, source, destination)
        print(json.dumps(result, indent=2))
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
