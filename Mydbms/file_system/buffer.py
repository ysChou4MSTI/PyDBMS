import numpy as np


class CircularLinkList:
    def __init__(self, capacity):
        self._capacity = capacity
        self._next = np.arange(capacity+1)
        self._last = np.arange(capacity+1)

    def _link(self, last_node, next_node):
        self._last[next_node] = last_node
        self._next[last_node] = next_node

    def remove(self, index):
        if self._last[index] == index:
            return
        self._link(self._last[index], self._next[index])
        self._last[index] = index
        self._next[index] = index
    """
    append to the first elemtent in the list head_last->index->head
    """
    def append(self, index): 
        self.remove(index)
        head = self._capacity
        self._link(self._last[head], index)
        self._link(index, head)
    """
    append to the last elemtent in the list and circulated to the head
    head->index->pre_last->->-->head
    """
    def insert_tail(self, index):  
        self.remove(index)
        head = self._capacity
        pre_last = self._next[head]
        self._link(head, index)
        self._link(index, pre_last)

    def get_tail(self):
        return self._next[self._capacity]
    

class Buffer:
    def __init__(self, capacity):
        self._capacity = capacity
        self.list = CircularLinkList(capacity)
        for i in range(capacity - 1, 0, -1):
            self.list.insert_tail(i)

    def find(self):
        """
        Here we use LRU to get an index for new data
        :return: next usable index
        """
        index = self.list.get_tail()
        self.list.remove(index)
        self.list.append(index)
        return index

    def free(self, index):
        """
        Here we free an index from buffer,
        so move it to the first to find
        :param index:
        :return:
        """
        self.list.insert_tail(index)

    def access(self, index):
        """
        We mark index when we access it by move it to last
        :param index:
        :return:
        """
        self.list.append(index)
