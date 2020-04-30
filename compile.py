#!/usr/bin/env python3

"""compile.py: Compiler script."""

# System imports
from classes import FQBN_Board_List, FQBN_Board_Details, Board_Picker_Menu, Notification_Box, Data_Loader, Menu_Pane, Menu_Item
from panes import Screen, InputEvent, Screen_Builder, TabChain
import sys
import os
import argparse
import subprocess 
import time
import json
import curses
import math

def current_s_time(): return time.time()

# 3rd party imports

from colorama import Fore, Back, Style, init


__author__ = "Keenan Nicholson"
__copyright__ = "Copyright 2020"
__credits__ = []
__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Keenan Nicholson"
__email__ = "keenanrnicholson@gmail.com"
__status__ = "Development"


##################################################

def main():

    print('Hello, world!')
    print(sys.version)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", help="activate the debugger (GDB)", action="store_true")
    args = parser.parse_args()
    print(args.debug)
    date = time.asctime()
    # fqbn = 'adafruit:samd:adafruit_metro_m4_airliftlite'
    fqbn = choose_fqbn_and_settings()
    # if fqbn is None:
        # return
    fqbn = 'adafruit:samd:adafruit_itsybitsy_m0'
    # comp(date, fqbn)
    pick_board_to_upload_program_to(date, fqbn)
        

def comp(date, fqbn):
    print(os.getcwd())
    command = f'arduino-cli compile --log-file "{os.getcwd()}/logs/{date} compile.txt" \
        --config-file "{os.getcwd()}/arduino-cli.yaml" \
        -b {fqbn} \
        --build-path "{os.getcwd()}/build/" \
        "{os.getcwd()}/cli_test"'
    try:
        res = subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print('err')
        print(e.output)


def choose_fqbn_and_settings(fqbn=None):
    if fqbn is None:
        devices_raw = subprocess.run(
            'arduino-cli board listall --format json', shell=True, capture_output=True)
        devices = json.loads(devices_raw.stdout)['boards']

        devices.sort(key=lambda item: item['FQBN'])

        for d in devices:
            print(d)  # {'name': 'Arduino Zero (Native USB Port)', 'FQBN': 'arduino:samd:arduino_zero_native'}

        if len(devices) == 0:
            print('No boards installed. Use the Arduino IDE to configure boards.')
            return None

        stdscr = curses_init()
        selection = curses.wrapper(fqbn_selector, devices)
        curses_destroy(stdscr)
        return None

def confirm():
    raise Exception('Confirm!')

def fqbn_selector(stdscr, devices):

    notification_box = Notification_Box(stdscr)
    data_loader = Data_Loader(devices, notification_pane=notification_box, save_data=True)
    board_list = FQBN_Board_List(stdscr, devices, data_loader, notification_pane=notification_box)
    board_details = FQBN_Board_Details(stdscr, devices, data_loader, board_list, notification_pane=notification_box)

    screen = Screen(stdscr, exit_key='q')

    menu = Menu_Pane(stdscr, Menu_Item('Confirm', confirm, hotkey='c', underline_char=0), Menu_Item('Exit', screen.external_exit, hotkey='q'))

    screen_builder = Screen_Builder(stdscr,                        6,     8,  title='Board Configuration')
    screen_builder.add_footer(notification_box)
    #                                            start_x, start_y, width, height, one_line=False
    screen_builder.add_pane(board_list,          0,       0,       2,     8)
    screen_builder.add_pane(board_details,       2,       0,       4,     7)
    screen_builder.add_pane(menu,                2,       7,       4,     1)

    # notification_obj.notify('Testing!!!', notification_duration=-1)
    screen.build(screen_builder)

    screen.add_processable_objects(data_loader)


    screen.init()

    interacting = True
    while interacting:
        interacting = screen.frame()

def pick_board_to_upload_program_to(date, fqbn):
    stdscr = curses_init()
    selection = curses.wrapper(upload, date, fqbn)
    curses_destroy(stdscr)


def upload2(stdscr, date, fqbn):
    notification_box = Notification_Box(stdscr)
    board_picker = Board_Picker_Menu(stdscr, fqbn, notification_box)
    # data_loader = Data_Loader(devices, notification_pane=notification_box, save_data=True)
    # board_list = FQBN_Board_List(stdscr, devices, data_loader, notification_pane=notification_box)
    # board_details = FQBN_Board_Details(stdscr, devices, data_loader, board_list, notification_pane=notification_box)

    screen = Screen(stdscr, exit_key='q')

    menu = Menu_Pane(stdscr, Menu_Item('Confirm', confirm, hotkey='c', underline_char=0), Menu_Item('Exit', screen.external_exit, hotkey='q'), subtle=True)

    screen_builder = Screen_Builder(stdscr,                        1,     4,  title='Avaliable Targets')
    screen_builder.add_footer(notification_box)
    #                                            start_x, start_y, width, height, one_line=False
    screen_builder.add_pane(board_picker,        0,       0,       1,     3)
    screen_builder.add_pane(menu,                0,       3,       1,     1)

    # notification_obj.notify('Testing!!!', notification_duration=-1)
    screen.build(screen_builder)

    # screen.add_processable_objects(data_loader)

    screen.init()

    interacting = True
    while interacting:
        interacting = screen.frame()

def upload(stdscr, date, fqbn):

    return upload2(stdscr, date, fqbn)

    print(f'Detecting Devices:')

    devices_raw = subprocess.run(
        'arduino-cli board list --format json', shell=True, capture_output=True)
    devices = json.loads(devices_raw.stdout)

    non_matching_board = []
    matching_boards = []
    other_ports = []
    longest_header = 0
    longest_content = 0
    for dev in devices:
        port = dev['address']
        proto = dev['protocol_label']
        if(len(port) + len(proto) + 1 > longest_header):
            longest_header = len(port) + len(proto) + 1
        if 'boards' in dev:
            entry = {'board': dev['boards'][0],
                     'port': dev['address'], 'proto': dev['protocol_label']}
            if len(entry['board']['name']) + len(entry['board']['FQBN']) + 3 > longest_content:
                longest_content = len(entry['board']['name']) + len(entry['board']['FQBN']) + 3
            if dev['boards'][0]['FQBN'] == fqbn:
                matching_boards.append(entry)
            else:
                non_matching_board.append(entry)
        else:
            other_ports.append({'port': dev['address'], 'proto': dev['protocol_label']})


    selection_required = False
    selection = None

    if len(matching_boards) != 1 or selection_required:  # It isn't obvious which board to upload to. Ask the user.
        stdscr = curses_init()
        if len(matching_boards) == 0:
            stdscr.addstr(0, 0, 'No boards detected to meet specified criteria. Press \'q\' to exit.')
        else:
            stdscr.addstr(0, 0, 'Multiple boards meet specified criteria. Press \'q\' to exit.')

        h, w = stdscr.getmaxyx()
        begin_x = 0
        begin_y = 2
        height = len(matching_boards) + len(non_matching_board) + len(other_ports) + 6
        width = w
        if height > h: # There isn't enough console height to display the prompt
            curses_destroy(stdscr)
            if len(matching_boards) > 1:
                print('Console too small to display device options. Selecting the first matching board.')
                selection = matching_boards[0]
            else:
                print('Console too small to display device options. No valid boards detected.')
                selection = None
        else:
            win = curses.newwin(height, width, begin_y, begin_x)
            selection = curses.wrapper(board_manager, win, matching_boards, non_matching_board, other_ports, longest_header, longest_content)
            curses_destroy(stdscr)
    else:  # It is obvious which board to upload to. User prompt not needed.
        selection = matching_boards[0]


    if selection is not None:

        print('Uploading')

        port = selection['port']
        command = f'arduino-cli upload --log-file "{os.getcwd()}/logs/{date} upload.txt" \
            --config-file "{os.getcwd()}/arduino-cli.yaml" \
            -b {fqbn} \
            -p {port} \
            "{os.getcwd()}/cli_test"'
        try:
            res = subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print('err')
            print(e.output)




def board_manager(stdscr, win, matching_boards, non_matching_board, other_ports, longest_header, longest_content):

    c = None

    num_options = len(matching_boards) + len(non_matching_board) + len(other_ports)
    selected_board_id = 0

    selecting = True
    escape = False

    list_boards(matching_boards, non_matching_board, other_ports, longest_header, longest_content, selected_board_id, False, win)
    stdscr.refresh()
    while selecting:
        while c != 10:  # Enter key
            if c == 258:  # Down Arrow
                selected_board_id = selected_board_id + 1
                if selected_board_id > num_options:
                    selected_board_id = num_options 
            elif c == 336:  # Shift-Down Arrow
                selected_board_id = selected_board_id + 5
                if selected_board_id > num_options - 1:
                    selected_board_id = num_options
            elif c == 259:  # Up Arrow
                selected_board_id = selected_board_id - 1
                if selected_board_id < 0:
                    selected_board_id = 0
            elif c == 337:  # Shift-Up Arrow
                selected_board_id = selected_board_id - 5
                if selected_board_id < 0:
                    selected_board_id = 0
            elif c == ord('q'):  # Q Key
                selecting = False
                escape = True
                break
            list_boards(matching_boards, non_matching_board, other_ports, longest_header, longest_content, selected_board_id, False, win)
            stdscr.refresh()
            time.sleep(0.1)
            c = stdscr.getch()

        if escape != True:
            list_boards(matching_boards, non_matching_board, other_ports, longest_header, longest_content, selected_board_id, True, win)
            stdscr.refresh()
            c = stdscr.getch()
            if c == 10:
                selecting = False

    if escape != True:
        board_list_total = []
        for board in matching_boards:
            board_list_total.append(board)
        for board in non_matching_board:
            board_list_total.append(board)
        for o_port in other_ports:
            board_list_total.append(o_port)
        return board_list_total[selected_board_id]
    else:
        return None

def list_boards(matching_boards, non_matching_board, other_ports, longest_header, longest_content, selected, confirm, win):

    height, width = win.getmaxyx()
    win.addstr(0, 0, '┌' + ' Port List '.center(width-2, '─') + '┐')

    board_list_total = []

    sel_false = '[ ]'
    sel_true = '[X]'
    counter = 0
    line_offset = 1
    for board in matching_boards:
        port = board['port']
        proto = board['proto']
        name = board['board']['name']
        found_fqbn = board['board']['FQBN']
        header = f'{port}:{proto}'.ljust(longest_header + 1, ' ')
        if selected == counter:
            sel = sel_true
        else:
            sel = sel_false
        sel_text = f'{sel} {counter}: '
        win.addstr(counter + line_offset, 0, '│ ')  # Default
        win.addstr(counter + line_offset, 2, sel_text, curses.color_pair(1))  # Default
        win.addstr(counter + line_offset, len(sel_text) + 2, f'{header}|\n', curses.color_pair(1))  # Default
        win.addstr(counter + line_offset, len(sel_text) + len(header) + 4, f'{name}', curses.color_pair(5))  # Yellow
        win.addstr(counter + line_offset, len(sel_text) + len(header) + len(name) + 4, ':', curses.color_pair(1))  # Default
        win.addstr(counter + line_offset, len(sel_text) + len(header) + len(name) + 5, f'{found_fqbn}\n', curses.color_pair(7))  # Cyan

        win.addstr(counter + line_offset, width-1, '│')  # Default

        # win.addstr(counter + line_offset, 0, f'{sel} {counter}: {Style.DIM}{header}|{Style.NORMAL} {Fore.YELLOW + name + Fore.RESET}:{Style.BRIGHT + Fore.CYAN+found_fqbn + Fore.RESET + Style.NORMAL}\n')
        counter = counter + 1
        board_list_total.append(board)

    for board in non_matching_board:
        port = board['port']
        proto = board['proto']
        name = board['board']['name']
        found_fqbn = board['board']['FQBN']
        header = f'{port}:{proto}'.ljust(longest_header + 1, ' ')
        if selected == counter:
            sel = sel_true
        else:
            sel = sel_false
        sel_text = f'{sel} {counter}: '
        win.addstr(counter + line_offset, 0, '│ ')  # Default
        win.addstr(counter + line_offset, 2, sel_text, curses.color_pair(1))  # Default
        win.addstr(counter + line_offset, len(sel_text) + 2, f'{header}|\n', curses.color_pair(2))  # Default Dim
        win.addstr(counter + line_offset, len(sel_text) + len(header) + 4, f'{name}', curses.color_pair(6))  # Yellow Dim
        win.addstr(counter + line_offset, len(sel_text) + len(header) + len(name) + 4, ':', curses.color_pair(2))  # Default Dim
        win.addstr(counter + line_offset, len(sel_text) + len(header) + len(name) + 5, f'{found_fqbn}\n', curses.color_pair(8))  # Cyan Dim

        win.addstr(counter + line_offset, width-1, '│')  # Default

        # win.addstr(counter + line_offset, 0, f'{sel} {counter}: {Style.DIM}{header}| {Fore.YELLOW + name + Fore.RESET}:{Fore.CYAN+found_fqbn}{Style.NORMAL+Fore.RESET}\n')
        counter = counter + 1
        board_list_total.append(board)

    for o_port in other_ports:
        port = o_port['port']
        proto = o_port['proto']
        header = f'{port}:{proto}'.ljust(longest_header + 1, ' ')
        if selected == counter:
            sel = sel_true
        else:
            sel = sel_false
        sel_text = f'{sel} {counter}: '
        win.addstr(counter + line_offset, 0, '│ ')  # Default
        win.addstr(counter + line_offset, 2, sel_text, curses.color_pair(2))  # Default
        win.addstr(counter + line_offset, len(sel_text) + 2, f'{header}|\n', curses.color_pair(2))  # Default Dim

        win.addstr(counter + line_offset, width-1, '│')  # Default

        # win.addstr(counter + line_offset, 0, f'{sel} {counter}: {Style.DIM}{header}|{Style.NORMAL}\n', curses.color_pair(3))
        counter = counter + 1
        board_list_total.append(o_port)

    ##### Empty (cancel)
    cancel_index = counter
    if selected == counter:
        sel = sel_true
    else:
        sel = sel_false
    sel_text = f'{sel} {counter}: '
    win.addstr(counter + line_offset, 0, '│ ')  # Default
    win.addstr(counter + line_offset, 2, sel_text, curses.color_pair(2))  # Default
    win.addstr(counter + line_offset, len(sel_text) + 2, 'Cancel', curses.color_pair(2))  # Default Dim
    win.addstr(counter + line_offset, width-1, '│')  # Default
    counter = counter + 1

    win.addstr(counter + line_offset, 0, '└' + ''.center(width-2, '─') + '┘')
    counter = counter + 1

    counter = counter + 1
    ##### End Empty (cancel)

    if not confirm:
        selected_prompt = f'Select a target: [{selected}]:'
        win.addstr(counter + line_offset, 0, selected_prompt)
        win.clrtoeol()
        if selected == cancel_index:
            win.addstr(counter + line_offset, len(selected_prompt)+1, 'Cancel')
        else:
            if 'board' in board_list_total[selected]:
                port = board_list_total[selected]['port'] + ' : '
                name = board_list_total[selected]['board']['name']
                found_fqbn = board_list_total[selected]['board']['FQBN']
                win.addstr(counter + line_offset, len(selected_prompt)+1, port)
                win.addstr(counter + line_offset, len(selected_prompt)+len(port)+1, name, curses.color_pair(5))
                win.addstr(counter + line_offset, len(selected_prompt)+len(port)+len(name)+1, ':')
                win.addstr(counter + line_offset, len(selected_prompt)+len(port)+len(name)+2, found_fqbn, curses.color_pair(7))
            else:
                win.addstr(counter + line_offset, len(selected_prompt)+1, board_list_total[selected]['port'])
    else:
        selected_prompt = f'Selected [{selected}]:'
        win.addstr(counter + line_offset, 0, selected_prompt)
        win.clrtoeol()
        if selected == cancel_index:
            win.addstr(counter + line_offset, len(selected_prompt)+1, 'Cancel?')
        else:
            if 'board' in board_list_total[selected]:
                name = board_list_total[selected]['board']['name']
                found_fqbn = board_list_total[selected]['board']['FQBN']
                win.addstr(counter + line_offset, len(selected_prompt)+1, name, curses.color_pair(5) | curses.A_UNDERLINE)
                win.addstr(counter + line_offset, len(selected_prompt)+len(name)+1, ':', curses.A_UNDERLINE)
                win.addstr(counter + line_offset, len(selected_prompt)+len(name)+2, found_fqbn, curses.color_pair(7) | curses.A_UNDERLINE)
                win.addstr(counter + line_offset, len(selected_prompt)+len(name)+len(found_fqbn)+2, '? (Enter to accept)')
            else:
                win.addstr(counter + line_offset, len(selected_prompt)+1, board_list_total[selected]['port'] , curses.A_UNDERLINE)
                win.addstr(counter + line_offset, len(selected_prompt)+len(board_list_total[selected]['port'])+1, '? (Enter to accept)')




    win.refresh()
    

    # for dev in devices:
    #     port = dev['address']
    #     proto = dev['protocol_label']
    #     if 'boards' in dev:
    #         entry = {'board': dev['boards'][0],
    #              'port': dev['address'], 'proto': dev['protocol_label']}
    #         boards.append(entry)
            
    #         name = entry['board']['name']
    #         found_fqbn = entry['board']['FQBN']
    #         if dev['boards'][0]['FQBN'] == fqbn or True:
    #             matching_boards.append(entry)
    #             print(f'{Style.DIM}{port}:{proto}{Style.NORMAL} {Fore.YELLOW + name + Fore.RESET}:{Style.BRIGHT + Fore.CYAN+found_fqbn + Fore.RESET + Style.NORMAL}')
    #         else:
        #         print(f'{Style.DIM}{port}:{proto} {Fore.YELLOW + name + Fore.RESET}:{Fore.CYAN+found_fqbn}{Style.NORMAL+Fore.RESET}')
        # else:
        #     print(f'{Style.DIM}{port}:{proto}{Style.NORMAL}')


    # if(len(matching_boards) == 0):
    #     print(f'{Fore.RED}No boards attach that match the specified target "{fqbn}":{Fore.RESET}')
    #     for b in boards:
    #         port = b['port']
    #         proto = b['proto']
    #         name = b['board']['name']
    #         found_fqbn = b['board']['FQBN']
    #         print(f'{port}:{proto}:{name}:{found_fqbn}')


    # else:
    #     for b in matching_boards:
    #         # print(b)
    #         pass


    # command = f'arduino-cli upload --log-file "{os.getcwd()}/logs/{date} upload.txt" \
        # --config-file "{os.getcwd()}/arduino-cli.yaml" \
        # -b adafruit:samd:adafruit_metro_m4_airliftlite \
        # --build-path "{os.getcwd()}/build/" \
        # "{os.getcwd()}/cli_test"'


def title(win, line, title, focused, unfocused_line_color=None, focused_line_color=None, unfocused_title_color=None, focused_title_color=None):
    if unfocused_line_color is None:
        unfocused_line_color = curses.color_pair(1)
    if focused_line_color is None:
        focused_line_color = curses.color_pair(1)
    if unfocused_title_color is None:
        unfocused_title_color = curses.color_pair(2)
    if focused_title_color is None:
        focused_title_color = curses.color_pair(5)


    line_color = focused_line_color if focused else unfocused_line_color
    title_color = focused_title_color if focused else unfocused_title_color


    _, w = win.getmaxyx()
    title_complete = f' {title} '
    fillerl = ''.ljust(math.ceil((w-2)/2 - len(title_complete)/2), '─')
    fillerr = ''.ljust(math.floor((w-2)/2 - len(title_complete)/2), '─')
    win.addstr(line, 0, '┌' + fillerl, line_color)
    win.addstr(line, len(fillerl) + 1, title_complete, title_color)
    win.addstr(line, len(fillerl) + len(title_complete) + 1, fillerr + '┐', line_color)


def curses_init():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    curses.mousemask(1)
    curses.use_default_colors()
    curses.init_pair(1, -1, -1)
    curses.init_pair(2, 240, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, 89, -1) # Dim red
    curses.init_pair(5, curses.COLOR_YELLOW, -1)
    curses.init_pair(6, 137, -1) # Dim yellow
    curses.init_pair(7, curses.COLOR_CYAN, -1)
    curses.init_pair(8, 76, -1) # Dim Cyan
    curses.init_pair(9, curses.COLOR_GREEN, -1)
    curses.init_pair(10, 23, -1) # Dim Green

    curses.init_pair(11, 235, -1) # Extra dim white

    curses.init_pair(12, -1, 235) # Extra dim white BG

    curses.curs_set(0)
    stdscr.nodelay(True)

    stdscr.clear()
    stdscr.refresh()

    init()
    return stdscr


def curses_destroy(stdscr):
    curses.echo()
    curses.nocbreak()
    stdscr.keypad(False)
    curses.endwin()
    curses.mousemask(0)
    curses.curs_set(1)



 
##################################################

if __name__ == '__main__':
    main()
    # stdscr = curses.initscr()
    # curses.noecho()
    # curses.cbreak()
    # stdscr.keypad(True)
    # curses.start_color()
    # curses.use_default_colors()
    # curses.init_pair(1, -1, -1)
    # curses.init_pair(2, 240, -1)
    # curses.init_pair(3, curses.COLOR_RED, -1)
    # curses.init_pair(4, 89, -1) # Dim red
    # curses.init_pair(5, curses.COLOR_YELLOW, -1)
    # curses.init_pair(6, 137, -1) # Dim yellow
    # curses.init_pair(7, curses.COLOR_CYAN, -1)
    # curses.init_pair(8, 76, -1) # Dim Cyan
    # curses.init_pair(9, curses.COLOR_GREEN, -1)
    # curses.init_pair(10, 23, -1) # Dim Green
    # try:
    #     # main()
    #     # curses.wrapper(main)

    #     curses.start_color()
    #     curses.use_default_colors()
    #     for i in range(0, curses.COLORS):
    #         curses.init_pair(i + 1, i, -1)
    #     try:
    #         for i in range(0, 255):
    #             stdscr.addstr(str(i), curses.color_pair(i))
    #     except curses.ERR:
    #         # End of screen reached
    #         pass
    #     stdscr.getch()
    # finally:
    #     curses.echo()
    #     curses.nocbreak()
    #     stdscr.keypad(False)
    #     curses.endwin()
