"""python -m hizashi_agent --house h12 --port 9012"""
import argparse
import logging

import uvicorn

from hizashi_shared import config, street


def main() -> None:
    parser = argparse.ArgumentParser(prog="hizashi_agent")
    parser.add_argument("--house", required=True, choices=sorted(config.AGENT_PORTS))
    parser.add_argument("--port", type=int)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format=f"%(asctime)s {args.house} %(name)s %(message)s")
    from .server import build_app

    # street.json is on the same machine as the hub; mandates come from the hub later (R1.5).
    house = street.load_houses()[args.house]
    uvicorn.run(build_app(house), host=args.host, port=args.port or config.AGENT_PORTS[args.house],
                log_level="warning")


if __name__ == "__main__":
    main()
