import time
from futu import OrderBookHandlerBase, StockQuoteHandlerBase, CurKlineHandlerBase, TickerHandlerBase, RTDataHandlerBase, BrokerHandlerBase
from futu import RET_OK, RET_ERROR

class OrderBookTest(OrderBookHandlerBase):
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(OrderBookTest,self).on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print("OrderBookTest: error, msg: %s" % data)
            return RET_ERROR, data
        print("OrderBookTest ", data) # OrderBookTest 自己的处理逻辑
        return RET_OK, data