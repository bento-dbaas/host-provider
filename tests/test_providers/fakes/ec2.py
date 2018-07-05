from collections import namedtuple

NodeSize = namedtuple("EC2BasicInfo", "id, extra, ram")


LIST_SIZES = [
    NodeSize(1, {'cpu': 1}, 512),
    NodeSize(2, {'cpu': 1}, 1024),
    NodeSize(3, {'cpu': 2}, 1024)
]
