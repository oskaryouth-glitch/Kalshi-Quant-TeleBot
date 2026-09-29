import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))                     # research/edge_search
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "price_test_1"))
