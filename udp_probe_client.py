
import socket
import time
import csv
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="10.0.0.2")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--csv", default="udp_results.csv")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout)
    results = []

    try:
        for seq in range(1, args.count + 1):
            message = f"probe-{seq}".encode()
            start = time.perf_counter()
            sock.sendto(message, (args.host, args.port))

            try:
                data, _ = sock.recvfrom(1024)
                rtt_ms = (time.perf_counter() - start) * 1000
                received = data.decode(errors="replace")
                lost = 0
                print(f"Probe {seq}: reply={received}, RTT={rtt_ms:.3f} ms")
            except socket.timeout:
                rtt_ms = ""
                lost = 1
                print(f"Probe {seq}: TIMEOUT (packet lost)")

            results.append([seq, args.host, rtt_ms, lost])
            time.sleep(0.2)
    finally:
        sock.close()

    with open(args.csv, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["sequence", "destination", "rtt_ms", "lost"])
        writer.writerows(results)

    lost_count = sum(row[3] for row in results)
    loss_percent = lost_count / args.count * 100
    print(f"\nPacket loss: {lost_count}/{args.count} ({loss_percent:.1f}%)")
    print(f"Results saved to {args.csv}")

if __name__ == "__main__":
    main()
