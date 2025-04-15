# distributed-router-sim-Multithreaded-
A toy project simulating a distributed routing protocol using multithreading and TCP sockets. Built for learning, but actually quite fun.

A multithreaded routing protocol simulator written in raw Python, simulating dynamic network topologies, inter-node message passing via TCP sockets, and routing updates using the Bellman-Ford algorithm.  
Originally built for a systems programming course (COMP3221, University of Sydney), later extended and hacked around — this is not production code, just an overengineered toy.

## 🚀 Features

- 🧅 Multi-threaded message handling using `threading.Thread`, `Lock`, `Event`, and `Queue`
- 🌐 TCP socket-based communication between neighbors
- 🛡️ Periodic routing broadcasts (configurable intervals)
- ⚙️ Interactive command support:
  - `FAIL`, `RECOVER`, `CHANGE`: simulate network changes
  - `MERGE`, `SPLIT`: mutate the topology (experimental)
  - `QUERY`, `QUERY PATH`: view current shortest paths
  - `CYCLE DETECT`: detect routing loops
  - `RESET`, `BATCH`: reset state or run scripted input

## 📁 Project Structure

```
.
├── main.py             # Core simulation engine and threads
├── Routing.sh          # Launches multiple nodes
├── test.sh             # Start nodes with necessary command
├── A.txt – F.txt       # Network config files per node
```

Each `.txt` file defines neighbors in the form:

```
<neighbor node> <cost> <port>
```

Example (`A.txt`):
```
2
B 1.0 6001
C 2.0 6002
```

## 🛠 How to Run

To run all nodes at once (A–F) with demo setting:

```bash
./test.sh
```

Or manually run a single node:

```bash
python3 main.py A 6000 A.txt 2 1
python3 main.py <node name> <port> <config file name> <seconds before initial routing print> <broadcast update interval>
```

Where:
- `A` = node ID
- `6000` = this node's TCP port
- `A.txt` = neighbor config file
- `2` = seconds before initial routing print
- `1` = broadcast update interval in seconds

## 🧪 Sample Commands

You can input commands directly into a node terminal:

```
QUERY E
QUERY PATH A F
CHANGE C 9
FAIL D
RECOVER D
MERGE B C
CYCLE DETECT
RESET
```


## Challenses that I solved during the projects:

- Race conditions, dead locks, dead locks caused by recursively calling functions, lots lots of error handling for multi-thread and socket system.
- Race condition caused by socket not yet start --need to wait until thread been ready by calling Event Ready Check.
- This is not a production system — it has race conditions, shared state soup, and some commands like `MERGE`/`SPLIT` are partially functional.
- Sockets is not reusable after failure.
- All threading coordination (including deadlock resolution) is manual.
- But hey — it works. Mostly.

## 📚 Academic Context

Originally written for COMP3221 (Computer Systems Programming) at the University of Sydney, but the final version was heavily modified for fun, exploration, and late-night debugging pain.

## 👤 Author

Aaron Zhang

