import socket
import sys
import threading
import queue
import time
import os
import json
import heapq


class Node:
    def __init__(self, name: str, routing_table: dict, port_num: int, file_name: str):
        self.name = name
        self.routing_table_lock = threading.Lock()
        self.routing_table = routing_table
        self.neighbours = set()
        self.neighbours.update(self.routing_table.keys())
        self.neighbours_lock = threading.Lock()
        self.lock = threading.Lock()
        self.port_num = port_num
        self.q = queue.Queue()
        self.mapping_dic = {}
        self.mapping_dic_lock = threading.Lock()
        self.all_nodes_dic = {}
        self.all_nodes_dic_lock = threading.Lock()
        self.socket_map = {}
        self.socket_map_lock = threading.Lock()
        self.failed = {}
        self.failed_lock = threading.Lock()
        self.active = True
        my_neighbours_dic = {"time": time.time()}
        for i in self.neighbours:
            my_neighbours_dic[i] = self.routing_table[i][1]
            # self.all_nodes_dic[i] = {"time": 0}
        self.all_nodes_dic[self.name] = my_neighbours_dic
        self.receiving_connection_thread_ready = threading.Event()
        self.connection_thread_ready = threading.Event()
        self.file_name = file_name
        self.running = threading.Event()

    def is_running(self):
        return not self.running.is_set()

    @staticmethod
    def creat_by_read_file(name, file_name: str, port_num: int):
        try:
            with open(file_name) as f:
                lines = f.readlines()
                routing_table = {}
                try:
                    num = int(lines[0])
                except:
                    print(f"Error: Invalid configuration file format. (First line must be an integer.)", flush=True)
                    os._exit(1)
                for i in range(1, int(lines[0]) + 1):
                    if len(lines[i].strip().split()) > 3:
                        print("Error: Invalid configuration file format.", flush=True)
                        os._exit(1)
                    try:
                        next_node, cost, port_num = lines[i].strip().split()
                        routing_table[next_node] = [next_node, float(cost), int(port_num)]
                    except:
                        print("Error: Invalid configuration file format. (Each neighbour entry must have exactly three tokens; cost must be numeric.)", flush=True)
                        os._exit(1)
        except FileNotFoundError:
            print(f"Error: Configuration file {file_name} not found.", flush=True)
            os._exit(1)
        return Node(name, routing_table, port_num, file_name)

    def stdout(self):
        with self.routing_table_lock, self.neighbours_lock:
            text = f'UPDATE {self.name} '
            for i in sorted(self.neighbours):
                if self.routing_table[i][1] == float('inf'):
                    continue
                with self.failed_lock:
                    if i in self.failed:
                        self.routing_table[i][1] = float('inf')
                        continue
                text += f"{i}:{self.routing_table[i][1]}:{self.routing_table[i][2]},"
            return text[:-1]

    def sending_broadcast_thread(self, interval: float):
        while self.is_running():
            time.sleep(interval)
            if not self.active:
                continue
            self.sending_broadcast()
            # threading.Thread(target=self.sending_broadcast).start()
        """
    def sending_broadcast_without_printing(self):
        
        with self.socket_map_lock, self.neighbours_lock, self.routing_table_lock:
            text = self.send_socket()
            for i in self.neighbours:
                if i not in self.socket_map:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_address = ('127.0.0.1', self.routing_table[i][2])
                    client_socket.connect(server_address)
                    self.socket_map[i] = client_socket
                try:
                    self.socket_map[i].send(text.encode('utf-8'))
                except:
                    self.safe_exit()
        """
    def sending_broadcast(self):
        print(self.stdout())
        with self.socket_map_lock, self.neighbours_lock, self.routing_table_lock:
            text = self.send_socket()
            for i in self.neighbours:
                if i not in self.socket_map:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_address = ('127.0.0.1', self.routing_table[i][2])
                    client_socket.connect(server_address)
                    self.socket_map[i] = client_socket
                self.socket_map[i].send(text.encode('utf-8'))

    def send_socket(self):
        # UPDATE1 {node.name} normal_std + " " + json.dumps(self.all_nodes_dic)
        with self.all_nodes_dic_lock, self.failed_lock:
            text = f'UPDATE1 {self.name} '
            for i in self.routing_table.keys():
                if self.routing_table[i][1] == float('inf') or i in self.failed:
                    continue
                text += f"{i}:{self.routing_table[i][1]}:{self.routing_table[i][2]},"
            text = text[:-1]
            my_neighbours_dic = {"time": time.time()}
            for i in self.neighbours:
                my_neighbours_dic[i] = self.routing_table[i][1]
            self.all_nodes_dic[self.name] = my_neighbours_dic
            text += " " + json.dumps(self.all_nodes_dic, separators=(',', ':'))
            return text + "\n"

    def update1_routing_table(self, source_node: str, command: str, json_all_nodes: str):
        changed = False
        if source_node == self.name:
            return
        with self.all_nodes_dic_lock, self.routing_table_lock:
            try:
                new_all_nodes_dic: dict = json.loads(json_all_nodes)
            except Exception as e:
                print(e, self.name, json_all_nodes)
            if new_all_nodes_dic[source_node][self.name] != self.routing_table[source_node][1]:
                changed = True
                self.all_nodes_dic[self.name][source_node] = new_all_nodes_dic[source_node][self.name]
                self.all_nodes_dic[self.name]["time"] = time.time()
                self.routing_table[source_node][1] = new_all_nodes_dic[source_node][self.name]
            for i in new_all_nodes_dic.keys():
                if i not in self.all_nodes_dic or new_all_nodes_dic[i]['time'] > self.all_nodes_dic[i]['time']:
                    self.all_nodes_dic[i] = new_all_nodes_dic[i]
        with self.routing_table_lock, self.neighbours_lock:
            ls = command.split(",")
            for i in ls:
                i_node, i_cost, i_port = i.split(':')
                i_cost = float(i_cost)
                i_port = int(i_port)
                if i_node == self.name:
                    continue
                elif i_node not in self.routing_table or self.routing_table[i_node][1] > (
                        i_cost + self.routing_table[source_node][1]):
                    if i_node in self.neighbours:
                        changed = True
                    with self.all_nodes_dic_lock:
                        if i_node in self.neighbours and i_node not in self.all_nodes_dic[source_node]:
                            self.routing_table[i_node] = [source_node, self.query_cost_no_print(self.name, i_node), i_port]
                        else:
                            self.routing_table[i_node] = [source_node, i_cost + self.routing_table[source_node][1], i_port]
        if changed:
            self.routing_calculation_thread()
            print(self.stdout())


    def update_routing_table(self, source_node: str, command: str):
        changed = False
        if source_node == self.name:
            return
        with self.lock, self.routing_table_lock, self.all_nodes_dic_lock, self.neighbours_lock:
            ls = command.split(",")
            messeager_neighbour = {"time": time.time()}
            for i in ls:
                i_node, i_cost, i_port = i.split(':')
                i_cost = float(i_cost)
                i_port = int(i_port)
                messeager_neighbour[i_node] = i_cost
                if i_node == self.name:
                    continue
                elif i_node not in self.routing_table or self.routing_table[i_node][1] > (
                        i_cost + self.routing_table[source_node][1]):
                    if i_node in self.neighbours:
                        changed = True
                    self.routing_table[i_node] = (source_node, i_cost + self.routing_table[source_node][1], i_port)
            self.all_nodes_dic[self.name] = messeager_neighbour
        if changed:
            self.routing_calculation_thread()

    def listen_std_input(self):
        while self.is_running():
            try:
                self.q.put(input().strip())
            except:
                pass

    def receiving_connection_thread(self, port_num: int):
        server_address = ('127.0.0.1', port_num)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # ✅ port reuse!!!!!!!! danger!!!!!!!!!!!
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ######  delet！！！！！！！！！
        server.bind(server_address)
        server.listen(1000)
        self.receiving_connection_thread_ready.set()
        while self.is_running():
            client_socket, client_address = server.accept()
            threading.Thread(target=self.procecing_socket_thread, args=[client_socket]).start()
        server.close()

    def procecing_socket_thread(self, client: socket.socket):
        buffer = ''
        while self.is_running():
            buffer += client.recv(4096).decode("utf-8")
            if not buffer:
                break
            temp = buffer.split("\n")
            if len(temp) == 1:
                continue
            for i in range(len(temp) - 1):
                self.q.put(temp[i].strip())
            buffer = temp[-1]
        client.close()

    def routing_calculation_thread(self):
        with self.all_nodes_dic_lock, self.failed_lock:
            total = max((len(self.all_nodes_dic) - len(self.failed) - 1), len(self.all_nodes_dic[self.name]))
            # if not self.active:
                # return
        found = 0
        routing_dic = {}
        hq = []
        with self.all_nodes_dic_lock:
            for i in self.all_nodes_dic[self.name]:
                with self.failed_lock, self.routing_table_lock:
                    if i == "time" or i in self.failed:
                        continue
                    heapq.heappush(hq, (self.routing_table[i][1], i, self.name + i))
        while found < total and hq and self.is_running():
            cur_cost, cur_name, cur_path = heapq.heappop(hq)
            if cur_name in routing_dic:
                continue
            routing_dic[cur_name] = (cur_path, cur_cost)
            found = found + 1
            with self.all_nodes_dic_lock:
                if cur_name not in self.all_nodes_dic:
                    continue
                cur_neighbours_dic = self.all_nodes_dic[cur_name]
            for i in cur_neighbours_dic:
                with self.failed_lock, self.routing_table_lock:
                    if i == "time" or i in routing_dic or i not in self.routing_table or i in self.failed:
                        continue
                    heapq.heappush(hq, (cur_neighbours_dic[i] + cur_cost, i, cur_path + i))
        text = f'I am Node {self.name}\n'
        for i in sorted(routing_dic):
            # if routing_dic[i][1] == float(inf)
            text += f"Least cost path from {self.name} to {i}: {routing_dic[i][0]}, link cost: {routing_dic[i][1]}\n"
        print(text[:-1])

    def query_path_thread(self, source_node: str, target_node: str):
        with self.all_nodes_dic_lock, self.failed_lock:
            total = len(self.all_nodes_dic) - len(self.failed) - 1
            if source_node not in self.all_nodes_dic:
                print("error error source or target node not in the all_nodes_dic")
                return
        found = 0
        routing_dic = {}
        hq = []
        with self.all_nodes_dic_lock:
            for i in self.all_nodes_dic[source_node]:
                with self.failed_lock, self.routing_table_lock:
                    if i == "time" or i in self.failed or i not in self.all_nodes_dic:
                        continue
                    heapq.heappush(hq, (self.all_nodes_dic[source_node][i], i, source_node + i))
        while found < total and hq and target_node not in routing_dic and self.is_running():
            cur_cost, cur_name, cur_path = heapq.heappop(hq)
            if cur_name in routing_dic:
                continue
            routing_dic[cur_name] = (cur_path, cur_cost)
            found = found + 1
            with self.all_nodes_dic_lock:
                if cur_name not in self.all_nodes_dic:
                    continue
                cur_neighbours_dic = self.all_nodes_dic[cur_name]
                for i in cur_neighbours_dic:
                    with self.failed_lock:
                        if i == "time" or i in routing_dic or i not in self.all_nodes_dic or i in self.failed:
                            continue
                        heapq.heappush(hq, (cur_neighbours_dic[i] + cur_cost, i, cur_path + i))
        text = f"Least cost path from {source_node} to {target_node}: {routing_dic[target_node][0]}, link cost: {routing_dic[target_node][1]}"
        print(text)

    def query_cost_no_print(self, source_node: str, target_node: str):
        with self.all_nodes_dic_lock, self.failed_lock:
            total = len(self.all_nodes_dic) - len(self.failed) - 1
            if source_node not in self.all_nodes_dic:
                print("error error source or target node not in the all_nodes_dic")
                return
        found = 0
        routing_dic = {}
        hq = []
        with self.all_nodes_dic_lock:
            for i in self.all_nodes_dic[source_node]:
                with self.failed_lock, self.routing_table_lock:
                    if i == "time" or i in self.failed or i not in self.all_nodes_dic:
                        continue
                    heapq.heappush(hq, (self.all_nodes_dic[source_node][i], i, source_node + i))
        while found < total and hq and target_node not in routing_dic and self.is_running():
            cur_cost, cur_name, cur_path = heapq.heappop(hq)
            if cur_name in routing_dic:
                continue
            routing_dic[cur_name] = (cur_path, cur_cost)
            found = found + 1
            with self.all_nodes_dic_lock:
                if cur_name not in self.all_nodes_dic:
                    continue
                cur_neighbours_dic = self.all_nodes_dic[cur_name]
                for i in cur_neighbours_dic:
                    with self.failed_lock:
                        if i == "time" or i in routing_dic or i not in self.all_nodes_dic or i in self.failed:
                            continue
                        heapq.heappush(hq, (cur_neighbours_dic[i] + cur_cost, i, cur_path + i))
        return routing_dic[target_node][1]

    def print_routing_by_time_thread(self, delay: float):
        time.sleep(delay)
        self.routing_calculation_thread()
        print(self.stdout())

    def process_listening(self):
        while self.is_running():
            content = self.q.get().split()
            if len(content) == 0:
                continue
            self.batch_processing(content)

    def batch_processing(self, content: list):
        # if content[0] != "UPDATE1":
            # print(content)
        if content[0] == "UPDATE":
            self.update_routing_table(content[1], content[2])
            self.routing_calculation_thread()
        elif content[0] == "CHANGE":
            try:
                if len(content) > 3:
                    self.safe_exit("Error: Invalid command format. Expected exactly two tokens after CHANGE.")
                with self.all_nodes_dic_lock:
                    if content[1] not in self.all_nodes_dic[self.name] or content[1] == self.name:
                        return
                    self.all_nodes_dic[self.name][content[1]] = float(content[2])
                    self.all_nodes_dic[self.name]["time"] = time.time()
                    if content[1] in self.all_nodes_dic:
                        self.all_nodes_dic[content[1]][self.name] = float(content[2])
                        self.all_nodes_dic[content[1]]["time"] = time.time()
                with self.routing_table_lock:
                    self.routing_table[content[1]][1] = float(content[2])
                self.routing_calculation_thread()
                print(self.stdout())

                # threading.Thread(target=self.sending_broadcast).start()
            except Exception as e:
                self.safe_exit("Error: Invalid command format. Expected numeric cost value.")


        elif content[0] == "FAIL":
            try:
                if len(content) != 2:
                    self.safe_exit("Error: Invalid command format. Expected: FAIL <Node-ID>.")
                if content[1] == self.name:
                    print(f"Node {self.name} is now DOWN.")
                    self.active = False
                    self.failed[content[1]] = 0
                    return
                else:
                    with self.failed_lock, self.routing_table_lock:
                        if content[1] in self.routing_table:
                            self.failed[content[1]] = self.routing_table[content[1]][1]
                            self.routing_table[content[1]][1] = float('inf')
                            self.routing_calculation_thread()
                            print(self.stdout())
                        else:
                            self.safe_exit("Error: Invalid command format. Expected a valid Node-ID.")
            except Exception as e:
                self.safe_exit("Error: Invalid command format. Expected a valid Node-ID.")

        elif content[0] == "RECOVER":
            try:
                if len(content) != 2:
                    self.safe_exit("Error: Invalid command format. Expected exactly: RECOVER <Node-ID>.")
                with self.routing_table_lock:
                    if content[1] not in self.routing_table:
                        self.safe_exit("Error: Invalid command format. Expected a valid Node-ID.")
                if content[1] == self.name:
                    print(f"Node {self.name} is now UP.")
                    self.active = True
                    self.failed.pop(content[1])
                else:
                    with self.failed_lock, self.routing_table_lock:
                        if content[1] in self.routing_table:
                            self.routing_table[content[1]][1] = self.failed[content[1]]
                            self.failed.pop(content[1])
                self.routing_calculation_thread()
                print(self.stdout())
            except:
                self.safe_exit("Error: Invalid command format. Expected a valid Node-ID.")

        elif content[0] == "QUERY":
            if content[1] == "PATH":
                try:
                    if len(content) != 4:
                        raise ValueError
                    self.query_path_thread(content[2], content[3])
                except Exception as e:
                    self.safe_exit(
                        "Error: Invalid command format. Expected two valid identifiers for Source and Destination.")
            else:
                if len(content) != 2:
                    self.safe_exit("Error: Invalid command format. Expected exactly one tokens after QUERY.")
                try:
                    self.query_path_thread(self.name, content[1])
                except:
                    self.safe_exit(
                        "Error: Invalid command format. Expected a valid Destination.")

        elif content[0] == "MERGE":
            try:
                if not self.merge_graphs(content[1], content[2]):
                    return
                self.routing_calculation_thread()
                print(self.stdout())
            except:
                self.safe_exit("Error: Invalid command format. Expected two valid identifiers for MERGE.")

        elif content[0] == "SPLIT":
            if len(content) != 1:
                self.safe_exit("Error: Invalid command format. Expected exactly: SPLIT.")
            with self.failed_lock, self.routing_table_lock, self.all_nodes_dic_lock, self.neighbours_lock:
                all_node = sorted(self.all_nodes_dic.keys())
                k = len(all_node) // 2
                v1 = all_node[:k]
                v2 = all_node[k:]
                if self.name in v1:
                    for i in v2:
                        self.routing_table.pop(i, None)
                        self.all_nodes_dic.pop(i, None)
                        if i in self.neighbours:
                            self.neighbours.discard(i)
                            self.all_nodes_dic[self.name].pop(i, None)
                else:
                    for i in v1:
                        self.routing_table.pop(i, None)
                        self.all_nodes_dic.pop(i, None)
                        if i in self.neighbours:
                            self.neighbours.discard(i)
                            self.all_nodes_dic[self.name].pop(i, None)
                print("Graph partitioned successfully.")
            self.routing_calculation_thread()
            print(self.stdout())

        elif content[0] == "RESET":
            if len(content) != 1:
                self.safe_exit("Error: Invalid command format. Expected exactly: RESET.")
            self.reset()
            print(f"Node {self.name} has been reset.")
            self.routing_calculation_thread()
            print(self.stdout())

        elif content[0] == "CYCLE":
            if len(content) != 2:
                self.safe_exit("Error: Invalid command format. Expected exactly: CYCLE DETECT.")
            with self.all_nodes_dic_lock, self.failed_lock:
                if self.dfs_cycle_detect(set(), self.name):
                    print("Cycle detected.")
                else:
                    print("No cycle found.")

        elif content[0] == "BATCH":
            if len(content) != 3:
                self.safe_exit("Error: Invalid command format. Expected: BATCH UPDATE <Filename>.")
            with open(content[2]) as f:
                lines = f.readlines()
            for i in lines:
                self.batch_processing(i.strip().split())
            print("Batch update complete.")
            self.routing_calculation_thread()
            print(self.stdout())

        elif content[0] == "UPDATE1":
            self.update1_routing_table(content[1], content[2], content[3])
            return
        elif content[0] == "exit":
            self.running.set()
            return
        else:
            self.safe_exit("Error: Invalid update packet format.")


    def merge_graphs(self, node1, node2):
        with self.failed_lock, self.routing_table_lock, self.all_nodes_dic_lock, self.neighbours_lock:
            if node2 not in self.all_nodes_dic or node1 not in self.all_nodes_dic:
                return False

            if node2 == self.name:
                self.active = False
                self.failed[self.name] = 0
                return False

            if node2 in self.neighbours:
                self.neighbours.remove(node2)
                if node1 != self.name:
                    self.neighbours.add(node1)

            n1 = self.all_nodes_dic[node1]
            n2 = self.all_nodes_dic[node2]

            for i in n2:
                if i == "time":
                    continue
                if i not in n1:
                    n1[i] = n2[i]
                else:
                    n1[i] = min(n1[i], n2[i])

            if node1 == self.name:
                for i in n1:
                    if i == "time" or i == self.name:
                        continue
                    self.routing_table[i][1] = n1[i]
                    self.neighbours.add(i)

            self.all_nodes_dic[node1] = n1

            for i in self.all_nodes_dic:
                if node2 in self.all_nodes_dic[i]:
                    self.all_nodes_dic[i].pop(node2)
                if i in self.all_nodes_dic[node1]:
                    self.all_nodes_dic[i][node1] = n1[i]

            self.all_nodes_dic[node1]["time"] = time.time()
            self.all_nodes_dic.pop(node2)

            if node1 not in self.routing_table:
                if node2 in self.routing_table:
                    self.routing_table.pop(node2)
                print("Graph merged successfully.")
                return True
            self.routing_table[node1][1] = min(self.routing_table[node1][1], self.routing_table[node2][1])
            self.routing_table.pop(node2)
            print("Graph merged successfully.")
            return True

    def dfs_cycle_detect(self, visited: set, target_node: str, last=None):
        if target_node not in self.all_nodes_dic:
            return False
        visited.add(target_node)
        for i in self.all_nodes_dic[target_node]:
            if i == last or i == "time" or i in self.failed:
                continue
            if i in visited:
                return True
            if self.dfs_cycle_detect(visited, i, target_node):
                return True
        return False

    def reset(self):
        with open(self.file_name) as f:
            lines = f.readlines()
            routing_table = {}
            for i in range(1, int(lines[0]) + 1):
                next_node, cost, port_num = lines[i].strip().split()
                routing_table[next_node] = [next_node, float(cost), int(port_num)]
            with self.all_nodes_dic_lock, self.routing_table_lock, self.neighbours_lock:
                self.routing_table = routing_table
                self.neighbours = set()
                self.neighbours.update(self.routing_table.keys())
                my_neighbours_dic = {"time": time.time()}
                for i in self.neighbours:
                    my_neighbours_dic[i] = self.routing_table[i][1]
                self.all_nodes_dic = {self.name: my_neighbours_dic}

    def start_sockets_neighbours(self):
        for i in self.neighbours:
            with self.routing_table_lock:
                server_address = ('127.0.0.1', self.routing_table[i][2])
            for j in range(100):
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(server_address)
                    break
                except Exception as e:
                    time.sleep(0.06)
                    #print(e, f"error!!!! node {self.name} fail to connect node {i} for {j} times")
                    #print(server_address)
                    continue
            with self.socket_map_lock:
                self.socket_map[i] = client_socket
        self.connection_thread_ready.set()

    def safe_exit(self, message = ""):
        if message:
            print(message, flush=True)
        self.running.set()
        os._exit(1)

def main():
    if len(sys.argv) < 5:
        print("Error: Insufficient arguments provided. Usage: ./Routing.sh <Node-ID> <Port-NO> <Node-Config-File>", flush=True)

        os._exit(1)

    node_id = sys.argv[1]
    if len(node_id) != 1 or node_id.isdigit():
        print("Error: Invalid Node-ID.", flush=True)
        os._exit(1)
    try:
        port = int(sys.argv[2])
        if port < 6000:
            raise ValueError
    except:
        print("Error: Invalid Port number. Must be an integer.", flush=True)
        os._exit(1)
    file_name = sys.argv[3]
    delay = float(sys.argv[4])
    update_time = float(sys.argv[5])


    node = Node.creat_by_read_file(node_id, file_name, port)
    threading.Thread(target=node.receiving_connection_thread, args=[port]).start()
    threading.Thread(target=node.listen_std_input).start()
    threading.Thread(target=node.process_listening).start()
    node.receiving_connection_thread_ready.wait()
    node.start_sockets_neighbours()
    threading.Thread(target=node.sending_broadcast_thread, args=[update_time]).start()
    threading.Thread(target=node.print_routing_by_time_thread, args=[delay]).start()
    while True:
        time.sleep(1)

def my_test_main():
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    file_name = sys.argv[3]
    delay = sys.argv[4]
    update_time = float(sys.argv[5])
    # queues = {"listen": queue.Queue(), "update": queue.Queue(), "query": queue.Queue(), }
    node = Node.creat_by_read_file(node_id, file_name, port)
    threading.Thread(target=node.receiving_connection_thread, args=[port]).start()
    # threading.Thread(target=node.listen_std_input).start()
    threading.Thread(target=node.process_listening).start()
    node.receiving_connection_thread_ready.wait()
    node.start_sockets_neighbours()
    threading.Thread(target=node.sending_broadcast_thread, args=[update_time]).start()
    time.sleep(0.7)
    node.q.put("CYCLE DETECT")
    time.sleep(4)

    print("stopped finish")
    #print(node.routing_table)
    #print(node.all_nodes_dic)
    #print("r table")
    threading.Thread(target=node.routing_calculation_thread).start()
    node.q.put("CHANGE F 100")
    #node.q.put("FAIL A")
    #node.q.put("QUERY PATH A E")
    time.sleep(3)
    #node.q.put("RECOVER A")
    node.q.put("MERGE C E")
    #node.q.put("SPLIT")
    node.q.put("CYCLE DETECT")
    time.sleep(2)
    node.q.put("exit")
    print("should exit by now!!!!!!!!!!!!!~!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    time.sleep(5)
    print("not successsssssssss exit by now!!!!!!!!successssssssssssuccessssssssssssuccessssssssssssuccesssssssssss")
    node.running.set()

    os._exit(1)



if __name__ == "__main__":
    my_test_main()
    # main()

#test split

#will accept change, but when other node update with older change to my neighbour
