
#from exchange import Exchange
#from merkato import Merkato

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.lines import Line2D

import tkinter as tk
from tkinter import ttk

from operator import itemgetter
import random

LARGE_FONT= ("Verdana", 12)
style.use("ggplot")

"""
expected bot data format from merkato

{
"open_orders" : { "buy" : [(0.022, 0.5), 
                           (0.018, 1.5) ],
                  "sell"  : [(0.027, 0.5), 
                             (0.033,1.5) ]},
"filled_orders" :  {"buy" : [(0.022, 0.5, DD-MM-YY_HH:MM:SS), 
                             (0.018, 1.5, DD-MM-YY_HH:MM:SS) ],
                    "sell"  : [(0.027, 0.5 ,DD-MM-YY_HH:MM:SS), 
                              (0.033,1.5, DD-MM-YY_HH:MM:SS) ]},                          
"balances" : {"BTC" : 0.5121,
              "XMR": 15.2039},
"market" : (00.24,0.026),
"price"  : 0.025
                    
}
"""

class Graph(tk.Frame):

    def __init__(self, app, parent, stub=False, price_x=[], price_y=[], bought_x=[], bought_y=[], sold_x=[], sold_y=[],
                 x_lowest_sell_order=[], y_lowest_sell_order=[], x_highest_buy_order=[], y_highest_buy_order=[]):
        tk.Frame.__init__(self, parent)
        self.app = app
        self.parent = parent
        self.stub = stub
        self.x_axis_refresh = True # todo: button to turn this off
        self.x_axis_window_size = 31  # todo: button for changing this

        #self.label = tk.Label(self, text=self.parent.pair, font=LARGE_FONT)
        self.label = tk.Label(self, text="XMR_BTC", font=LARGE_FONT)

        self.label.pack(pady=10, padx=10)

        self.fig, self.ax = plt.subplots()

        self.x_price = price_x
        self.y_price = price_y
        self.line_price = Line2D(self.x_price, self.y_price, color="blue")
        self.ax.add_line(self.line_price)

        self.x_bought = bought_x
        self.y_bought = bought_y
        self.boughtScatter = self.ax.scatter(self.x_bought, self.y_bought, color="green")

        self.x_sold = sold_x
        self.y_sold = sold_y
        self.scatter_sold = self.ax.scatter(self.x_sold, self.y_sold, color="red")

        self.x_lowest_sell_order = x_lowest_sell_order
        self.y_lowest_sell_order = y_lowest_sell_order
        self.line_lowest_sell_order = Line2D(self.x_lowest_sell_order, self.y_lowest_sell_order, color="salmon")
        self.ax.add_line(self.line_lowest_sell_order)

        self.x_highest_buy_order = x_highest_buy_order
        self.y_highest_buy_order = y_highest_buy_order
        self.line_highest_buy_order = Line2D(self.x_highest_buy_order, self.y_highest_buy_order, color="lime")
        self.ax.add_line(self.line_highest_buy_order)

        #self.fig = Figure(figsize=(5, 5), dpi=100)
        #self.graph = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        #self.loop = animation.FuncAnimation(f, self.refresh,fargs = , interval=1000)

        if self.stub:
            self._root().after(5000, self.refresh, self.fake_data())


    def fake_data(self):
        data = {
                "price": (self.x_price[-1] + 1, self.y_price[-1] + random.randint(-5, 5))

                }
        print(repr(data))
        return data

    def date_formatter(self, date):
        # TODO: do something with date
        return date

    def refresh(self, data):
        """
        :param data: a dictionary that comes from bot update method.  todo: agree on format for data
        :return:
        """
        self.ax.clear()
        print("cleared self.ax")
        try:
            if "price" in data:
                px, py = data["price"]
                self.x_price.append(self.date_formatter(px))
                self.y_price.append(py)
            if self.x_price and self.y_price:
                self.line_price.set_data(self.x_price, self.y_price)
                self.ax.add_line(self.line_price)

            # -----------------------------------------------------

            if "filled_orders" in data:
                if "buy" in data["filled_orders"]:
                    for filled in data["filled_orders"]["buy"]:
                        bx = self.date_formatter(filled[2]) # date
                        by = filled[0]
                        self.x_bought.append(bx)
                        self.y_bought.append(by)
            if self.x_bought and self.y_bought:
                print(self.x_bought, self.y_bought)
                #self.boughtScatter.set_offsets((self.x_bought, self.y_bought))
                self.boughtScatter = self.ax.scatter(self.x_bought, self.y_bought, color="green")

            # -----------------------------------------------------
            if "filled_orders" in data:
                if "sell" in data["filled_orders"]:
                    for filled in data["filled_orders"]["sell"]:
                        sx = self.date_formatter(filled[2]) # date
                        sy = filled[0]
                        self.x_sold.append(sx)
                        self.y_sold.append(sy)
            if self.x_sold and self.y_sold:
                #self.scatter_sold.set_offsets((self.x_sold, self.y_sold))
                self.scatter_sold = self.ax.scatter(self.x_sold, self.y_sold, color="red")
            # -----------------------------------------------------
            order_price_index = 0  # sort on first element of tuple which should be price (for now)
            order_time_index = 2
            if "open_orders" in data:
                if "sell" in data["open_orders"]:
                    sell_data = data["open_orders"]["sell"]
                    if sell_data:
                        lowest_sell = sorted(sell_data, key=itemgetter(order_price_index))[0]
                        self.x_lowest_sell_order.append(self.date_formatter(lowest_sell[order_time_index]))
                        self.y_lowest_sell_order.append(lowest_sell[order_price_index])
                        if len(sell_data) > 1:   # then we have a meaningful "high" order
                            # todo: something with this data
                            highest_sell = sorted(sell_data, key=itemgetter(order_price_index))[-1]

                if "buy" in data["open_orders"]:
                    buy_data = data["open_orders"]["buy"]
                    if buy_data:
                        highest_buy = sorted(buy_data, key=itemgetter(order_price_index))[-1]
                        self.x_highest_buy_order.append(self.date_formatter(highest_buy[order_time_index]))
                        self.y_highest_buy_order.append(highest_buy[order_price_index])
                        if len(buy_data) > 1:   # then we have a meaningful "low" order
                            # todo: something with this data
                            lowest_buy = sorted(buy_data, key=itemgetter(order_price_index))[0]

            if self.x_lowest_sell_order and self.y_lowest_sell_order:
                self.line_lowest_sell_order.set_data(self.x_lowest_sell_order, self.y_lowest_sell_order)
                self.ax.add_line(self.line_lowest_sell_order)

            if self.x_highest_buy_order and self.y_highest_buy_order:
                self.line_highest_buy_order.set_data(self.x_highest_buy_order, self.y_highest_buy_order)
                self.ax.add_line(self.line_highest_buy_order)
            # -----------------------------------------------------
            if self.x_axis_refresh:
                if len(self.x_price) > self.x_axis_window_size:
                    plt.xlim(self.x_price[-1 * self.x_axis_window_size + 1], self.x_price[-1])
                    plt.autoscale(axis="y")
                else:
                    plt.autoscale()
            self.canvas.draw()

        except Exception as e:
            print(str(e))
            raise
        finally:
            if self.stub:
                self._root().after(5000, self.refresh, self.fake_data())




class Bot(ttk.Frame):
    def __init__(self,app, parent, exchange_config={}, pair="", *args, **kwargs):
        ttk.Frame.__init__(self, parent, style="app.TFrame", *args, **kwargs)
        self.app = app
        self.parent = parent
        # if background and not self.app.light:
        #     self.bg = tk.PhotoImage(file = background)
        #     self.bglabel = tk.Label(self, image=self.bg)
        #     self.bglabel.place(x=0, y=0, relwidth=1, relheight=1)
        self.pair = pair
        if not exchange_config:
            # get args via gui
            pass
        #self.bot = Merkato(exchange_config)
        self.heading = ttk.Label(self,text = self.pair,style = "heading.TLabel")
        """
        #self.body = VSFrame(self,fheight = 430,nobar = True)
        self.dest = Destination(self.app,self,name = "",cwidth = 40,select_handle = "Subaddress Book",background = "misc/genericspace.gif",mode = "receive")

        self.addresses = []

        #self.textAddress = MyWidget(self.app,self.body.interior,handle = "Address",choices = [self.app.initAddress],cwidth = 50,startVal =  self.app.initAddress )
        self.amountVar = tk.StringVar()
        self.dest.amount.value.config(textvariable = self.amountVar)
        self.new_label = MyWidget(self.app,self,handle = "New Subaddress",ewidth=23,choices = "entry",startVal = "<label goes here>")
        self.moon3 = tk.PhotoImage(file = "misc/moonbutton3.gif")
        if "monero" not in sys.argv[1]:
            self.new_button = tk.Button(self,text = "New Sub.",command =self.new_subaddress,highlightthickness=0,font=('Liberation Mono','12','normal'),foreground = "white",bd = 3,bg = "#2D89A0" )
        else:
            self.new_button = tk.Button(self,text = "New Sub.",command =self.new_subaddress,image = self.moon3,compound = tk.CENTER,height = 18,width = 60,highlightthickness=0,font=('Liberation Mono','12','normal'),foreground = "white",bd = 3,bg = "#900100" )
        #self.amount = MyWidget(self.app,self.body.interior,handle = "Amount",choices = "entry",optional = True,activeStart=False)
        #self.amount.value.configure(textvariable = self.amountVar)
        self.amountVar.trace("w", lambda name, index, mode, sv=self.amountVar: self.amountCallback(sv))
        #self.amount.optState.trace("w", lambda name, index, mode, sv=self.amountVar: self.amountCallback(sv))
        self.qr = ttk.Label(self,style = "app.TLabel")
        self.genQR()

        self.heading.grid(row=0,column=0,sticky = tk.W,pady= (10,15))
        #self.body.grid(row=1,column=0,sticky = tk.W+ tk.E,pady= (5,20))
        self.dest.grid(row=1,column=0,columnspan = 2,sticky = tk.W,padx = (15,15))
        self.new_label.grid(row=2,column=0,sticky = tk.W,padx = (109,0),pady=(15,0))
        self.new_button.grid(row=2,column=1,sticky = tk.W,padx = (0,10),pady=(25,0))
        #self.textAddress.grid(row=1,column=0,columnspan = 2,sticky = tk.W)
        #self.amount.grid(row=2,column=1,sticky = tk.E,pady= (10,0))
        self.qr.grid(row=3,column=0,sticky = tk.W+tk.E,padx=(140,0),pady= (15,80),columnspan = 3)
        """

if __name__ == "__main__":
    root = tk.Tk()
    targs = {
            "price_x" : [1,2,3,4,5,6,7,8,9,10],
            "price_y" : [250,250,240,240,250,260,260,240,230,260,],
            "bought_x" : [3,4,8,9],
            "bought_y" : [241,241,241,241],
            "sold_x" : [6,7,10],
            "sold_y" : [258,258,258],
            "x_lowest_sell_order" : [1,2,3,4,5,6,7,8,9,10],
            "y_lowest_sell_order" : [258, 258, 258, 258, 258, 258, 258, 258, 258, 258, ],
            "x_highest_buy_order" : [1,2,3,4,5,6,7,8,9,10],
            "y_highest_buy_order" : [241, 241, 241, 241, 241, 241, 241, 241, 241, 241, ],
            }
    test = Graph(root, root,stub = True, **targs)
    test.pack()

    root.mainloop()
