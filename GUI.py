import tkinter as tk
from tkinter import ttk
from Main import VolumeBot
import multiprocessing
import datetime
import prettytable
from prettytable import MSWORD_FRIENDLY  

window = tk.Tk()
window.title("Volume generation bot")
window.call("source", "azure.tcl")
window.call("set_theme", "light")

global process
processes = {}
num = 0

def update_processes():
    '''
        Continuously check for closed processes and remove them
    '''
    global processes
    for i in list(processes):
        if not processes[i][0].is_alive():
            processes[i][1].destroy()
            processes[i][2].destroy()
            processes.pop(i)
    
    window.after(100, update_processes)

def stop(i, lbl, btn):
    '''
        Stop a process
    '''
    global processes
    processes[i][0].terminate()
    processes.pop(i)
    lbl.destroy()
    btn.destroy()

def check_required_usdt():
    try:
        for k, v in processes.items():
            acc1_usdt = getattr(v[-1], "acc1_usdt")
            acc1_hvt = getattr(v[-1], "acc1_hvt")
            acc2_usdt = getattr(v[-1], "acc2_usdt")
            acc2_hvt = getattr(v[-1], "acc2_hvt")
            quantity_to_trade = getattr(v[-1], "quantity_to_trade")
            required_usdt = getattr(v[-1], "required_usdt")
            table = prettytable.PrettyTable(["      ", "Account 1", "Account 2"])
            table.add_row(["USDT", format(acc1_usdt, ".2f"), format(acc2_usdt, ".2f")])
            table.add_row(["HVT", format(acc1_hvt, ".2f"), format(acc2_hvt, ".2f")])
            # table.add_row(["Trading HVT quantity", quantity_to_trade, ""])
            # table.add_row(["Required USDT amount", required_usdt, ""])
            table.set_style(MSWORD_FRIENDLY)
            table.align = 'c'
            table.padding_width = 10
            print(acc1_hvt, acc2_hvt)
            # text_ = k[28:] + '\n' + f'    Account 1:          Account 2:' + '\n' + f'USDT:{acc1_usdt}         {acc2_usdt}' + '\n' + f'hvt:{acc1_hvt}         {acc2_hvt}' + '\n' + f'Trading quantity: {quantity_to_trade}'+ '\n' + f'Required USDT: {required_usdt}'
            text_ = k[28:] + '\n' + table.get_formatted_string(out_format = "text")+ '\n' + f'Trading quantity: {quantity_to_trade}'+ '\n' + f'Required USDT: {required_usdt}'
            v[-3].configure(text = text_)
    except Exception as e:
        print(e)
    window.after(1000, check_required_usdt)

def start():
    '''
        Start and stop a trader instance using multiprocessing
    '''
    if btn_start['text'] == 'Start':
        # Getting parameters from user input
        global processes, num
        trading_pair = ent_trading_pair.get().replace(' ','').strip().lower()
        
        # Validate trading pair input
        if not trading_pair:
            print("Error: Trading pair cannot be empty")
            return
        
        # Remove _usdt if user accidentally included it
        if trading_pair.endswith('_usdt'):
            trading_pair = trading_pair.replace('_usdt', '')
        
        min_time = float(ent_min_time.get().replace(' ',''))
        max_time = float(ent_max_time.get().replace(' ',''))
        wallet_percentage = float(ent_wallet_percentage.get().replace(' ',''))
        min_spread = float(ent_min_spread.get().replace(' ',''))
        max_spread = float(ent_max_spread.get().replace(' ',''))
        pause_volume = float(ent_pause_volume.get().replace(' ',''))
        buy_sell_ratio = float(ent_buy_sell_ratio.get().replace(' ',''))
        api_key1 = ent_apiKey1.get().replace(' ','')
        secret_key1 = ent_apiSecret1.get().replace(' ','')
        api_key2 = ent_apiKey2.get().replace(' ','')
        secret_key2 = ent_apiSecret2.get().replace(' ','')

        # Initialize a trader intance on another process,
        # to avoid blocking Tkinter's main loop
        main = VolumeBot(min_time, max_time, wallet_percentage, min_spread, max_spread, pause_volume, buy_sell_ratio, api_key1, secret_key1, api_key2, secret_key2, trading_pair)
        # main.cancel_pending_order()
        process = multiprocessing.Process(target = main.run)
        i = f'{datetime.datetime.now()}, {trading_pair}_usdt, {min_time}, {max_time}, {wallet_percentage}, {min_spread}, {max_spread}, {pause_volume}, {buy_sell_ratio}'
        processes[i] = [process]
        processes[i][0].start()

        lbl_processes = ttk.Label(master = frm_tasks, text = i[28:])
        lbl_processes.grid(row = num, column = 0, padx = 10, pady = 10)
        btn_stop = ttk.Button(master = frm_tasks, text = 'Stop', command = lambda: stop(i, lbl_processes, btn_stop))
        btn_stop.grid(row = num, column = 1, padx = 10, pady = 10)
        frm_tasks.update_idletasks()
        canva.config(scrollregion=canva.bbox("all"))

        processes[i].append(lbl_processes)
        processes[i].append(btn_stop)
        processes[i].append(main)
        num = num + 1

def load():
    filename = 'keys.txt'
    with open(filename, 'r') as file:
        lines = file.readlines()
        ent_apiKey1.delete(0, tk.END)
        ent_apiKey1.insert(0, str(lines[0].strip()))
        ent_apiSecret1.delete(0, tk.END)
        ent_apiSecret1.insert(0, str(lines[1].strip()))
        ent_apiKey2.delete(0, tk.END)
        ent_apiKey2.insert(0, str(lines[2].strip()))
        ent_apiSecret2.delete(0, tk.END)
        ent_apiSecret2.insert(0, str(lines[3].strip()))

if __name__ == '__main__':
    # Title
    lbl_title = ttk.Label(master = window, text = 'Volume bot', font = ("Helvetica",30, "italic"))
    lbl_title.grid(row = 0, column = 0, padx = 10, pady = 10, columnspan = 2)

    # Trading pair entry
    frm_trading_pair = ttk.Frame(master = window)
    ent_trading_pair = ttk.Entry(master = frm_trading_pair, width = 10)
    lbl_trading_pair = ttk.Label(master = frm_trading_pair, text = "Trading pair (e.g., mcoin for mcoin_usdt)")
    ent_trading_pair.grid(row = 0, column = 1, padx = 10)
    lbl_trading_pair.grid(row = 0, column = 0)
    ent_trading_pair.insert(0, 'mcoin')  # Default value
    frm_trading_pair.grid(row = 1, column = 0, padx = 10, pady = 10, sticky = "w")

    # Min time entry
    frm_min_time = ttk.Frame(master = window)
    ent_min_time = ttk.Entry(master = frm_min_time, width = 10)
    lbl_min_time = ttk.Label(master = frm_min_time, text = "Enter min time")
    ent_min_time.grid(row = 0, column = 1, padx = 10)
    lbl_min_time.grid(row = 0, column = 0)
    frm_min_time.grid(row = 2, column = 0, padx = 10, pady = 10, sticky = "w")

    # Max time entry
    frm_max_time = ttk.Frame(master = window)
    ent_max_time = ttk.Entry(master = frm_max_time, width = 10)
    lbl_max_time = ttk.Label(master = frm_max_time, text = "Enter max time")
    ent_max_time.grid(row = 0, column = 1, padx = 10)
    lbl_max_time.grid(row = 0, column = 0)
    # ent_max_time.insert(0, '50')
    frm_max_time.grid(row = 3, column = 0, padx = 10, pady = 10, sticky = "w")

    # Waller percentage entry
    frm_wallet_percentage = ttk.Frame(master = window)
    ent_wallet_percentage = ttk.Entry(master = frm_wallet_percentage, width = 10)
    lbl_wallet_percentage = ttk.Label(master = frm_wallet_percentage, text = "Enter wallet percentage")
    ent_wallet_percentage.grid(row = 0, column = 1, padx = 10)
    lbl_wallet_percentage.grid(row = 0, column = 0)
    frm_wallet_percentage.grid(row = 4, column = 0, padx = 10, pady = 10, sticky = "w")

    # Min spread
    frm_min_spread = ttk.Frame(master = window)
    ent_min_spread = ttk.Entry(master = frm_min_spread, width = 10)
    lbl_min_spread = ttk.Label(master = frm_min_spread, text = "Enter min spread")
    ent_min_spread.grid(row = 0, column = 1, padx = 10)
    lbl_min_spread.grid(row = 0, column = 0)
    # ent_min_spread.insert(0, '5')
    frm_min_spread.grid(row = 5, column = 0, padx = 10, pady = 10, sticky = "w")

    # Max spread
    frm_max_spread = ttk.Frame(master = window)
    ent_max_spread = ttk.Entry(master = frm_max_spread, width = 10)
    lbl_max_spread = ttk.Label(master = frm_max_spread, text = "Enter max spread")
    ent_max_spread.grid(row = 0, column = 1, padx = 10)
    lbl_max_spread.grid(row = 0, column = 0)
    # ent_max_spread.insert(0, '5')
    frm_max_spread.grid(row = 2, column = 1, padx = 10, pady = 10, sticky = "w")

    # Pause volume entry
    frm_pause_volume = ttk.Frame(master = window)
    ent_pause_volume = ttk.Entry(master = frm_pause_volume, width = 10)
    lbl_pause_volume = ttk.Label(master = frm_pause_volume, text = "Enter pause volume")
    ent_pause_volume.grid(row = 0, column = 1, padx = 10)
    lbl_pause_volume.grid(row = 0, column = 0)
    # ent_pause_volume.insert(0, '10')
    frm_pause_volume.grid(row = 3, column = 1, padx = 10, pady = 10, sticky = "w")

    # Buy sell ratio
    frm_buy_sell_ratio = ttk.Frame(master = window)
    ent_buy_sell_ratio = ttk.Entry(master = frm_buy_sell_ratio, width = 10)
    lbl_buy_sell_ratio = ttk.Label(master = frm_buy_sell_ratio, text = "Enter buy/sell ratio")
    ent_buy_sell_ratio.grid(row = 0, column = 1, padx = 10)
    lbl_buy_sell_ratio.grid(row = 0, column = 0)
    ent_buy_sell_ratio.insert(0, '0.5')
    frm_buy_sell_ratio.grid(row = 4, column = 1, padx = 10, pady = 10, sticky = "w")

    # API key 1 entry
    frm_apiKey1 = ttk.Frame(master = window)
    ent_apiKey1 = ttk.Entry(master = frm_apiKey1, width = 60)
    lbl_apiKey1 = ttk.Label(master = frm_apiKey1, text = "Enter API key account 1")
    ent_apiKey1.grid(row = 1, column = 0)
    lbl_apiKey1.grid(row = 0, column = 0)
    frm_apiKey1.grid(row = 9, column = 0, columnspan = 3, padx = 10, pady = 10)

    # API secret 1 entry
    frm_apiSecret1 = ttk.Frame(master = window)
    ent_apiSecret1 = ttk.Entry(master = frm_apiSecret1, width = 60)
    lbl_apiSecret1 = ttk.Label(master = frm_apiSecret1, text = "Enter API secret account 1")
    ent_apiSecret1.grid(row = 1, column = 0)
    lbl_apiSecret1.grid(row = 0, column = 0)
    frm_apiSecret1.grid(row = 10, column = 0, columnspan = 3, padx = 10, pady = 10)

    # API key 2 entry
    frm_apiKey2 = ttk.Frame(master = window)
    ent_apiKey2 = ttk.Entry(master = frm_apiKey2, width = 60)
    lbl_apiKey2 = ttk.Label(master = frm_apiKey2, text = "Enter API key account 2")
    ent_apiKey2.grid(row = 1, column = 0)
    lbl_apiKey2.grid(row = 0, column = 0)
    frm_apiKey2.grid(row = 11, column = 0, columnspan = 3, padx = 10, pady = 10)

    # API secret 2 entry
    frm_apiSecret2 = ttk.Frame(master = window)
    ent_apiSecret2 = ttk.Entry(master = frm_apiSecret2, width = 60)
    lbl_apiSecret2 = ttk.Label(master = frm_apiSecret2, text = "Enter API secret account 2")
    ent_apiSecret2.grid(row = 1, column = 0)
    lbl_apiSecret2.grid(row = 0, column = 0)
    frm_apiSecret2.grid(row = 12, column = 0, columnspan = 3, padx = 10, pady = 10)

    # Load button
    btn_load = ttk.Button(master = window, text = 'Load keys', command = load)
    btn_load.grid(row = 13, column = 0, columnspan = 1, padx = 10, pady = 10)

    # Start button
    btn_start = ttk.Button(master = window, text = 'Start', command = start)
    btn_start.grid(row = 13, column = 0, columnspan = 2, padx = 10, pady = 10)

    # Processes
    frm_processes = ttk.Frame(master = window)
    lbl_processes = ttk.Label(master = window, text = "Running processes:")
    lbl_processes.grid(row = 1, column = 4, columnspan = 2, padx = 10, pady = 10)
    frm_processes.grid(row = 2, column = 4, columnspan = 2, rowspan = 100, padx = 10, pady = 10)

    canva = tk.Canvas(frm_processes)
    canva.grid(row=0, column=0, sticky="news")
    sb = tk.Scrollbar(frm_processes, orient="vertical", command=canva.yview)
    sb.grid(row=0, column=1, sticky='ns')
    canva.configure(yscrollcommand=sb.set, width=550 + sb.winfo_width(),height=400)

    frm_tasks = tk.Frame(canva)
    canva.create_window((0, 0), window=frm_tasks, anchor='nw')
    frm_processes.config(width=550 + sb.winfo_width(),height=400)
    frm_tasks.config(width=550 + sb.winfo_width(),height=400)

    update_processes()
    # check_required_usdt()

    window.mainloop()
