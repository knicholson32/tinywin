import curses
import math
import time

from tinywin import core, helpers

class InputEvent(object):
    def __init__(self, key):
        self.key = key
        self._mouse_event = False
        if key == curses.KEY_MOUSE:
            try:
                self._id, self._mx, self._my, self._z, self._bstate = curses.getmouse()
                self._mouse_event = True
            except curses.error as e:
                pass

    def get_mouse(self):
        if self._mouse_event:
            self.absorb()
            return (self._id, self._mx, self._my, self._z, self._bstate)
        else:
            return None

    def absorb(self):
        self.key = None
        self._mouse_event = None

class TabChain(core.Processable):
    def __init__(self, *args, wrap=True):
        self.chain_order = []
        self._wrap = wrap
        for a in args:
            self.chain_order.append(a)

    def key_input(self, ie, update_focus_callback=None):
        if len(self.chain_order) == 0:
            return ie
        key = ie.key
        if key == 9:  # Tab
            if self.tab_forward(update_focus_callback=update_focus_callback):
                ie.absorb()
        elif key == 353:  # Rev Tab
            if self.tab_back(update_focus_callback=update_focus_callback):
                ie.absorb()
        return ie

    def tab_forward(self, update_focus_callback=None):
        selected_pane = None
        selected_index = 0
        for i in range(0, len(self.chain_order)):
            if self.chain_order[i]._focus is True:
                selected_pane = self.chain_order[i]
                selected_index = i
                break

        if selected_pane is None:
            self.chain_order[0].focus()
            update_focus_callback(self.chain_order[0])
            return True

        if selected_index == len(self.chain_order) - 1:
            if not self._wrap:
                # We're at the end of the list trying to tab forward. Not allowed.
                return False
            else:
                selected_index = -1

        selected_pane.unfocus()
        selected_index = selected_index + 1
        self.chain_order[selected_index].focus()
        update_focus_callback(self.chain_order[selected_index])
        return True

    def tab_back(self, update_focus_callback=None):
        selected_pane = None
        selected_index = 0
        for i in range(0, len(self.chain_order)):
            if self.chain_order[i]._focus is True:
                selected_pane = self.chain_order[i]
                selected_index = i
                break

        if selected_pane is None:
            self.chain_order[0].focus()
            update_focus_callback(self.chain_order[0])
            return True

        if selected_index == 0:
            if not self._wrap:
                # We're at the end of the list trying to tab backwards. Not allowed.
                return False
            else:
                selected_index = len(self.chain_order)

        selected_pane.unfocus()
        selected_index = selected_index - 1
        self.chain_order[selected_index].focus()
        update_focus_callback(self.chain_order[selected_index])
        return True

class Screen_Title(object):
    def __init__(self, height, width, y, x, title, no_title=False, draw_lower=False, lower_y=-1):
        super(Screen_Title, self).__init__()
        self._height = height
        self._width = width
        self._y = y
        self._x = x
        self._lower_y = lower_y
        if self._lower_y != -1:
            self._draw_lower = draw_lower
            self._lower_line = '─'*(self._width-2)
        else:
            self._draw_lower = False

        if no_title:
            self._title = ''
        else:
            self._title = ' ' + title + ' '
        self._fillerl = ''.ljust(math.ceil((self._width-2)/2 - len(self._title)/2), '─')
        self._fillerr = ''.ljust(math.floor((self._width-2)/2 - len(self._title)/2), '─')

        self._win = curses.newwin(self._height, self._width, self._y, self._x)

        if self._draw_lower:
            self._lower_win = curses.newwin(self._height, self._width, self._lower_y, self._x)

    def draw(self):
        self._win.addstr(0, 1, self._fillerl, curses.color_pair(2))
        self._win.addstr(0, 1 + len(self._fillerl), self._title, curses.color_pair(1))
        self._win.addstr(0, 1 + len(self._fillerl) + len(self._title), self._fillerr, curses.color_pair(2))
        self._win.refresh()

        if self._draw_lower:
            self._lower_win.addstr(0, 1, self._lower_line, curses.color_pair(2))
            self._lower_win.refresh()

class Screen_Builder(core.Processable):
    def __init__(self, stdscr, x_divs, y_divs, title=None):
        super(Screen_Builder, self).__init__()

        self._stdscr = stdscr
        # self._win = win
        self._x_divs = x_divs
        self._y_divs = y_divs
        self._panes = []

        self._h, self._w = self._stdscr.getmaxyx()


        self._pane_order_x_len = self._w
        self._pane_order_y_len = self._h
        self._pane_y_offset = -1
        self._pane_order = [[None]*self._pane_order_x_len for _ in range(self._pane_order_y_len-1)]

        self._y_offset = 0
        self._footer = None
        self._tab_order = None

        if title is not None:
            self._Screen_Title = Screen_Title(1, self._w, 0, 0, title, draw_lower=True, lower_y=self._h-1)
            self._h = self._h - 2
            self._y_offset = 1
        else:
            self._Screen_Title = None
        self.calc_per_block()
        self.current_focus = (0, 0)

    def calc_per_block(self):
        self._y_per_block = math.floor(self._h / self._y_divs)
        self._x_per_block = math.floor(self._w / self._x_divs)

    def unfocus_all(self):
        for p in self._panes:
            p.get_pane().unfocus()

    def get_panes(self):
        if self._footer is not None:
            l = self._panes.copy()
            l.append(self._footer)
            return l
        else:
            return self._panes

    def add_footer(self, footer):
        if self._footer is not None:
            raise Exception('This screen already has a footer object')
        self._footer = core.Pane_Holder(footer, 0, 0, 0, 0)


        win = curses.newwin(1,      self._w, self._h, 0)
        self._footer.link_win(win)

        self._h = self._h - 1
        self.calc_per_block()

    def add_tab_order(self, tab_order):
        self._tab_order = tab_order

    def add_pane(self, pane, start_x, start_y, width, height, one_line=False, fixed_to=None):
        ph = core.Pane_Holder(pane, start_x, start_y, width, height, one_line=one_line, fixed_to=fixed_to, unfocus_callback=self.unfocus_all)
        self.calculate_win_for_pane(ph)
        if len(self._panes) == 0:
            ph.get_pane().focus()
        self._panes.append(ph)

    def fill_in_pane_order(self, pane, height, width, start_y, start_x):
        pane.add_focus_cursor_data({
            'height': height,
            'width': width,
            'start_y': start_y,
            'start_x': start_x
        })
        # with open(f"Output-{str(pane)}-index.txt", "w") as text_file:
        for y in range(start_y, start_y + height-1):
            # print(str(y) + ':', end='', file=text_file)
            for x in range(start_x, start_x + width-1):
                try:
                    self._pane_order[y+self._pane_y_offset][x] = pane
                    # print(str(x) + ' ', file=text_file, end='')
                except IndexError as e:
                    # (51, 1), (117, 51)
                    raise IndexError(f'{(x, y)}, {(self._pane_order_x_len, self._pane_order_y_len)}')
            # print('', file=text_file)
        # print(f'{(self._pane_order_x_len, self._pane_order_y_len)}', file=text_file)
        # print('height, width, start_y, start_x', file=text_file)
        # print(f'{(pane, height, width, start_y, start_x)}', file=text_file)

        # with open(f"Output-{str(pane)}.txt", "w") as text_file:
        #     for i in range(len(self._pane_order)):
        #         for j in range(len(self._pane_order[i])):
        #             print(str(self._pane_order[i][j]) + ' ', end='', file=text_file)
        #         print('', file=text_file)
        #     print(f'{(self._pane_order_x_len, self._pane_order_y_len)}', file=text_file)
        #     print('height, width, start_y, start_x', file=text_file)
        #     print(f'{(pane, height, width, start_y, start_x)}', file=text_file)

        # matrix = self._pane_order
        # s = [[str(e) for e in row] for row in matrix]
        # lens = [max(map(len, col)) for col in zip(*s)]
        # fmt = ' '.join('{{:{}}}'.format(x) for x in lens)
        # table = [fmt.format(*row) for row in s]
        # output = '\n'.join(table)
        # with open(f"Output-{str(pane)}.txt", "w") as text_file:
        #     print(output, file=text_file)
        #     print(f'{(self._pane_order_x_len, self._pane_order_y_len)}', file=text_file)
        #     print(f'{(pane, height, width, start_y, start_x)}', file=text_file)

    def calculate_win_for_pane(self, ph, fixed_to=None):
        (x, y, w, h) = ph.get_coords()

        # Check that this pane will fit on the screen
        if x < 0 or y < 0:
            raise Exception(f'Invalid pane coordinate')
        if x + w > self._x_divs:
            raise Exception(f'Pane is too wide or overruns the bounds of the screen: {ph.get_pane().__class__} : x:{x+w} > x:{self._x_divs}')
        if y + h > self._y_divs:
            # raise Exception(f'Pane is too tall or overruns the bounds of the screen: {ph.get_pane().__class__} : y:{y+h} > y:{self._y_divs}')
            pass

        y_shift = 0
        x_shift = 0

        if y > 0:
            y_shift = -1

        if x > 0:
            x_shift = 0

        if ph.get_is_one_line():
            #                                      nlines,      ncols,                           begin_y,                                          begin_x
            win = curses.newwin(                   1 - y_shift, w * self._x_per_block - x_shift, y * self._y_per_block + self._y_offset + y_shift, x * self._x_per_block+x_shift)
            self.fill_in_pane_order(ph.get_pane(), 1 - y_shift, w * self._x_per_block - x_shift, y * self._y_per_block + self._y_offset + y_shift, x * self._x_per_block+x_shift)
        else:
            #                                      nlines,                          ncols,                           begin_y,                                          begin_x
            win = curses.newwin(                   h * self._y_per_block - y_shift, w * self._x_per_block - x_shift, y * self._y_per_block + self._y_offset + y_shift, x * self._x_per_block+x_shift)
            self.fill_in_pane_order(ph.get_pane(), h * self._y_per_block - y_shift, w * self._x_per_block - x_shift, y * self._y_per_block + self._y_offset + y_shift, x * self._x_per_block+x_shift)
        ph.link_win(win)

    def set_focus(self):
        (x, y) = self.current_focus
        pane = self._pane_order[y][x]
        if pane is not None:
            self.unfocus_all()
            pane.focus()
        else:
            raise Exception(f'No focus target at location ({x}, {y})')

    def set_focus_location_from_object(self, obj):
        index = -1
        for p in range(0, len(self._panes)):
            if obj == self._panes[p].get_pane():
                index = p
                break

        if index == -1:
            return

        if self._panes[index].get_pane().focus_cursor_data is not None:
            d = self._panes[index].get_pane().focus_cursor_data
            self.current_focus = (d['start_x'], d['start_y'])
            # raise Exception(self.current_focus)

    def move_focus(self, x_amt, y_amt):
        (x, y) = self.current_focus
        old_pane = self._pane_order[y][x]
        y_lim = len(self._pane_order)
        x_lim = len(self._pane_order[0])
        wrap_limiter = 2
        if (x_amt == 0 and y_amt == 0) or (x_amt != 0 and y_amt != 0):
            raise Exception(f'Invalid step: {(x_amt, y_amt)}')

        while (self._pane_order[y][x] == None or self._pane_order[y][x] == old_pane) and wrap_limiter > 0:
            if x_amt != 0:
                # move by x
                x = x + x_amt
            else:
                # move by y
                y = y + y_amt
            
            if x < 0:
                x = 0
                wrap_limiter = wrap_limiter - 1
            elif x > x_lim - 1:
                x = x_lim  - 1
                wrap_limiter = wrap_limiter - 1

            if y < 0:
                y = 0
                wrap_limiter = wrap_limiter - 1
            elif y > y_lim  - 1:
                y = y_lim  - 1
                wrap_limiter = wrap_limiter - 1


        if wrap_limiter == 0:
            # raise Exception(f'Wrapped {(x, y)}:{self._pane_order[y][x]}')
            return
        self.current_focus = (x, y)
        self.set_focus()

    def key_input(self, ie):
        tmp_ie = ie
        for p in self._panes:  # Process direct focus keys
            tmp_ie = p.key_input(tmp_ie)
            if tmp_ie.key is None:
                return tmp_ie

        if self._tab_order is not None:
            tmp_ie = self._tab_order.key_input(tmp_ie, update_focus_callback=self.set_focus_location_from_object)

        if ie.key == 259:  # Up Arrow
            self.move_focus(0, -1)
        elif ie.key == 258:  # Down Arrow
            self.move_focus(0, 1)
        elif ie.key == 261:  # Right Arrow
            self.move_focus(1, 0)
        elif ie.key == 260:  # Left Arrow
            self.move_focus(-1, 0)
        else:
            return tmp_ie

        tmp_ie.absorb()
        return tmp_ie

    def draw(self): # TODO: Make this a one-time draw instead of every frame
        if self._Screen_Title is not None:
            self._Screen_Title.draw()

class Screen(object):
    def __init__(self, stdscr, exit_key='q', process_rate_ps=30, frame_rate_ps=15):
        super(Screen, self).__init__()

        self._stdscr = stdscr
        self._h, self._w = self._stdscr.getmaxyx()

        self.drawable_objects = []
        self.processable_objects = []

        self._exit_key = ord(exit_key)

        self._last_draw_time = time.time()
        self._last_process_time = self._last_draw_time
        self._last_action_time = self._last_draw_time


        self._process_rate_ps = process_rate_ps
        self._draw_rate_ps = frame_rate_ps

        self._time_between_processes = 1 / self._process_rate_ps
        self._time_between_draws = 1 / self._draw_rate_ps

        self._ie = None

        self._force_close = False

        self._screen_builder = None

    def external_exit(self):
        self._force_close = True

    def build(self, screen_builder):
        self.load_screen_builder(screen_builder)
        for pane in screen_builder.get_panes():
            pane_obj = pane.get_pane()
            if isinstance(pane_obj, core.Drawable):
                self.drawable_objects.append(pane_obj)
            elif isinstance(pane_obj, core.Processable):
                self.processable_objects.append(pane_obj)

        with open("Output.txt", "w") as text_file:
            print('-:  ', end='', file=text_file)
            for j in range(0, len(self._screen_builder._pane_order[0])):
                print(f'{j} '.ljust(4, ' '), end='', file=text_file)
            print('', file=text_file)
            for i in range(0, len(self._screen_builder._pane_order)):
                print(f'{i}: '.ljust(4, ' '),end='', file=text_file)
                for j in range(0, len(self._screen_builder._pane_order[0])):
                    p = self._screen_builder._pane_order[i][j]
                    if p is None:
                        print(f'0   ', end='', file=text_file)
                    else:
                        print(f'{str(p)}   ', end='', file=text_file)
                print('', file=text_file)
            print(f'{(self._screen_builder._pane_order_x_len, self._screen_builder._pane_order_y_len)}', file=text_file)


        # matrix = self._screen_builder._pane_order
        # s = [[str(e) for e in row] for row in matrix]
        # lens = [max(map(len, col)) for col in zip(*s)]
        # fmt = ' '.join('{{:{}}}'.format(x) for x in lens)
        # table = [fmt.format(*row) for row in s]
        # output = '\n'.join(table)
        # with open("Output.txt", "w") as text_file:
        #     print(output, file=text_file)
        #     print(f'{(self._screen_builder._pane_order_x_len, self._screen_builder._pane_order_y_len)}', file=text_file)

    def init(self):
        for p in self.processable_objects:
            if isinstance(p, core.Init):
                p.init()
        for d in self.drawable_objects:
            if isinstance(d, core.Init):
                d.init()

    def load_screen_builder(self, sb):
        if self._screen_builder is not None:
            raise Exception('Screen already has a screen builder object')
        self._screen_builder = sb
        if self._screen_builder._tab_order is None:
            panes = self._screen_builder._panes
            p_list = []
            for p in panes:
                p_list.append(p.get_pane())
            self._screen_builder.add_tab_order(TabChain(*p_list))

    def add_processable_objects(self, *obj):
        for o in obj:
            self.processable_objects.append(o)

    def add_drawable_objects(self, *obj):
        for o in obj:
            self.drawable_objects.append(o)

    def frame(self):

        if self._force_close:
            return False

        current_time = time.time()

        time_until_next_process = (self._last_process_time + self._time_between_processes) - current_time
        time_until_next_draw = (self._last_process_time + self._time_between_processes) - current_time

        process_due = time_until_next_process <= 0
        draw_due = time_until_next_draw <= 0

        if not process_due and not draw_due:
            if time_until_next_process < time_until_next_draw:
                time.sleep(time_until_next_process)
            else:
                time.sleep(time_until_next_draw)
        else:
            if process_due:
                self.process(current_time)
            if draw_due:
                self.draw(current_time)


        c = self._stdscr.getch()
        self._ie = InputEvent(c)
        if c != -1:
            curses.flushinp()
        self._ie = self.key_input(self._ie)
        if self._screen_builder is not None:
            self._ie = self._screen_builder.key_input(self._ie)
        if self._ie is not None and self._ie.key == self._exit_key:
            return False

        self.process(current_time)
        self.draw(current_time)
        
        self._last_action_time = current_time
        return True

    def key_input(self, ie):
        tmp_ie = ie
        for p in self.processable_objects:
            tmp_ie = p.key_input(tmp_ie)
        for d in self.drawable_objects:
            tmp_ie = d.key_input(tmp_ie)
        return tmp_ie

    def process(self, current_time):
        for p in self.processable_objects:
            p.process(current_time)
        for d in self.drawable_objects:
            d.process(current_time)
        self._last_process_time = current_time

    def draw(self, current_time):
        for d in self.drawable_objects:
            d.draw()

        if self._screen_builder is not None:
            self._screen_builder.draw()

        self._last_draw_time = current_time
