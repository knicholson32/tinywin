import curses
import math

def title(win, line, title, focused, unfocused_line_color=None, focused_line_color=None, unfocused_title_color=None, focused_title_color=None, omit_side_borders=False):
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

    left_corner = '┌' if not omit_side_borders else ' '
    right_corner = '┐' if not omit_side_borders else ' '

    _, w = win.getmaxyx()
    if title != '':
        title_complete = f' {title} '
        fillerl = ''.ljust(math.ceil((w-2)/2 - len(title_complete)/2), '─')
        fillerr = ''.ljust(math.floor((w-2)/2 - len(title_complete)/2), '─')
        win.addstr(line, 0, left_corner + fillerl, line_color)
        win.addstr(line, len(fillerl) + 1, title_complete, title_color)
        win.addstr(line, len(fillerl) + len(title_complete) + 1, fillerr + right_corner, line_color)
    else:
        fillerl = ''.ljust(math.ceil((w-2)/2), '─')
        fillerr = ''.ljust(math.floor((w-2)/2), '─')
        win.addstr(line, 0, left_corner + fillerl, line_color)
        win.addstr(line, len(fillerl) + 1, fillerr + right_corner, line_color)

def curses_init():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    # curses.mousemask(1)
    curses.mousemask(-1)
    curses.use_default_colors()
    curses.init_pair(1, -1, -1)
    curses.init_pair(2, 240, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, 89, -1)  # Dim red
    curses.init_pair(5, curses.COLOR_YELLOW, -1)
    curses.init_pair(6, 137, -1)  # Dim yellow
    curses.init_pair(7, curses.COLOR_CYAN, -1)
    curses.init_pair(8, 76, -1)  # Dim Cyan
    curses.init_pair(9, curses.COLOR_GREEN, -1)
    curses.init_pair(10, 23, -1)  # Dim Green

    curses.init_pair(11, 235, -1)  # Extra dim white

    curses.init_pair(12, -1, 235)  # Extra dim white BG

    curses.curs_set(0)
    stdscr.nodelay(True)
    # stdscr.notimeout(True)

    stdscr.clear()
    stdscr.refresh()

    return stdscr

def curses_destroy(stdscr):
    curses.echo()
    curses.nocbreak()
    stdscr.keypad(False)
    curses.endwin()
    curses.mousemask(0)
    curses.curs_set(1)


curses_mouse_states = {
    curses.BUTTON1_PRESSED: 'Button 1 Pressed',
    curses.BUTTON1_RELEASED: 'Button 1 Released',
    curses.BUTTON1_CLICKED: 'Button 1 Clicked',
    curses.BUTTON1_DOUBLE_CLICKED: 'Button 1 Double-Clicked',
    curses.BUTTON1_TRIPLE_CLICKED: 'Button 1 Triple-Clicked',

    curses.BUTTON2_PRESSED: 'Button 2 Pressed',
    curses.BUTTON2_RELEASED: 'Button 2 Released',
    curses.BUTTON2_CLICKED: 'Button 2 Clicked',
    curses.BUTTON2_DOUBLE_CLICKED: 'Button 2 Double-Clicked',
    curses.BUTTON2_TRIPLE_CLICKED: 'Button 2 Triple-Clicked',

    curses.BUTTON3_PRESSED: 'Button 3 Pressed',
    curses.BUTTON3_RELEASED: 'Button 3 Released',
    curses.BUTTON3_CLICKED: 'Button 3 Clicked',
    curses.BUTTON3_DOUBLE_CLICKED: 'Button 3 Double-Clicked',
    curses.BUTTON3_TRIPLE_CLICKED: 'Button 3 Triple-Clicked',

    curses.BUTTON4_PRESSED: 'Button 4 Pressed',
    curses.BUTTON4_RELEASED: 'Button 4 Released',
    curses.BUTTON4_CLICKED: 'Button 4 Clicked',
    curses.BUTTON4_DOUBLE_CLICKED: 'Button 4 Double-Clicked',
    curses.BUTTON4_TRIPLE_CLICKED: 'Button 4 Triple-Clicked',

    curses.BUTTON_SHIFT: 'Button Shift',
    curses.BUTTON_CTRL: 'Button Ctrl',
    curses.BUTTON_ALT: 'Button Alt',

    134217728: 'REPORT_MOUSE_POSITION'
}

REPORT_MOUSE_POSITION = 134217728
