class FGES:
    def __init__(self, data, penalty=1.0):
        self.data = data.values
        n = len(data.columns)
        self.nodes = list(range(n))
        self.edges = {node: set() for node in self.nodes}
        self.parents = {node: set() for node in self.nodes}
        # Each column is, given the parents of this node, add the node in the row.
        self.BICS = np.zeros((n, n))
        self.penalty = penalty
        self.init_BICS()

    def BIC(self, X, y):
        return BIC(X, y, self.penalty)

    def check_adjacency(self, x, y):
        return (y in self.edges[x]) or (x in self.edges[y]) or (x == y)

    def directed(self, x, y):
        return (y in self.edges[x]) and not(x in self.edges[y])

    def undirected(self, x, y):
        return (x in self.edges[y]) and (y in self.edges[y])

    def apply_meek_rules(self):
        for node in self.nodes:
            for adj in self.edges[node]:
                for double_adj in self.edges[adj]:

                    # Rule 1: Away from collider
                    if self.directed(node, adj):
                        if self.undirected(adj, double_adj) and not(check_adjacency(node, double_adj)):
                            self.edges[double_adj].remove(adj)
                            self.parents[double_adj].add(adj)

                    # Rule 2: Away from cycle
                        if self.directed(adj, double_adj) and self.undirected(double_adj, node):
                            self.edges[double_adj].remove(node)
                            self.parents[double_adj].add(node)

                    # Rule 3: Double triangle
                    else:
                        if self.undirected(adj, double_adj):
                            mutuals = self.edges[node] & self.edges[adj] & self.edges[double_adj]
                            for target in mutuals:
                                if self.directed(node, target) and self.directed(double_adj, target) and self.undirected(adj, target):
                                    self.edges[target].remove(adj)
                                    self.parents[target].add(adj)

    def CPDAG(self):
        for node in self.nodes:
            for adj in self.edges[node]:
                if self.directed(node, adj):
                    v_struct = False
                    for double_adj in self.parents[adj]:
                        if not(self.check_adjacency(node, double_adj)):
                            v_struct = True
                            break
                        else:
                            continue
                    if not v_struct:
                        self.edges[adj].add(node)
                        self.parents[adj].remove(node)

    def init_BICS(self):
        n = len(self.nodes)
        for i in range(n):
            y = self.data[:, i]
            for j in range(i+1, n):
                X = self.data[:, j]
                self.BICS[i, j] = self.BIC(X, y)
                self.BICS[j, i] = self.BICS[i, j]

    def add_edge(self):
        # Buscamos el maximo de los BICS de añadir un arco, si es menor que 0
        # no mejoramos con ningún arco y paramos.
        if np.amax(self.BICS) <= 0:
            return False
        # Cogemos el indice del arco a añadir. Vamos a introducir j como padre
        # de i.
        i, j = np.unravel_index(np.argmax(self.BICS), self.BICS.shape)

        def _add(A, B):
            # Comprobamos que i, j no esten conectados ya (no deberia pasar)
            if B in set(self.edges[A]) or B in set(self.edges[A]):
                self.BICS[j, i], self.BICS[i, j] = 0, 0
                return True
            # Añadimos j a los padres de i.
            self.parents[A].add(B)

            for edge in list(self.edges[A]):
                self.parents[A].add(edge)
                self.edges[A].remove(edge)

        _add(i, j)

        Ai = list(self.parents[i])
        data_i = self.data[:, Ai]
        y_i = self.data[:, i]

        for node in set(self.nodes) - set((i, j)):
            data_node = self.data[:, node].reshape(-1, 1)
            if node not in Ai:
                X = np.hstack((data_i, data_node))
                self.BICS[node, i] = self.BIC(X, y_i) - self.BICS[j, i]

        self.BICS[j, i], self.BICS[i, j] = 0, 0
        self.CPDAG()
        self.apply_meek_rules()
        return True

    def init_BICS_deletion(self):
        n = len(self.nodes)
        self.BICS = np.zeros((n, n))
        for node in self.nodes:
            Adj = list(self.edges[node])
            if not Adj:
                continue

            y = self.data[:, node]
            data_n = self.data[:, Adj]
            start_BIC = self.BIC(data_n, y)
            if len(Adj) <= 1:
                continue
            for edge in Adj:
                data_n = self.data[:, tuple(set(Adj)-{edge})]
                self.BICS[edge, node] = self.BIC(data_n, y) - start_BIC

    def delete_edge(self):
        if np.amax(self.BICS) <= 0:
            return False

        j, i = np.unravel_index(np.argmax(self.BICS), self.BICS.shape)
        self.edges[i].remove(j)
        self.parents[i].remove(i)

        Adj = list(self.edges[i])
        y = self.data[:, i]
        data_n = self.data[:, Adj]
        start_BIC = self.BIC(data_n, y)

        for edge in Adj:
            X = self.data[:, tuple(set(Adj)-{edge})]
            self.BICS[edge, i] = self.BIC(data_n, y) - start_BIC
            self.BICS[i, edge] = self.BICS[edge, i]

        self.BICS[j, i], self.BICS[i, j] = 0, 0
        self.CPDAG()
        self.apply_meek_rules()
        return True
