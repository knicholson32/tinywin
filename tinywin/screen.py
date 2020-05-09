import curses
import math
import time

from tinywin import core, helpers

class Input_Event(object):
    def __init__(self, key):
        self.key = key
        self._mouse_event = False
        if key == curses.KEY_MOUSE:
            try:
                # mouse_res = curses.getmouse()
                # raise Exception(mouse_res[4])
                self._id, self._mx, self._my, self._z, self._bstate = curses.getmouse()
                self._mouse_event = True
            except curses.error as e:
                # We can't use this mouse event, so absorb it
                self.absorb()

    def get_mouse(self):
        if self._mouse_event:
            self.absorb()
            return (self._id, self._mx, self._my, self._z, self._bstate)
        else:
            return None

    def absorb(self):
        self.key = None
        self._mouse_event = None

class Tab_Chain(core.Processable):
    def __init__(self, *args, wrap=True):
        self.chain_order = []
        self._wrap = wrap
        for a in args:
            self.chain_order.append(a)

    def key_input(self, ie):
        if len(self.chain_order) == 0:
            return ie
        key = ie.key
        if key == 9:  # Tab
            if self.tab_forward():
                ie.absorb()
        elif key == 353:  # Rev Tab
            if self.tab_back():
                ie.absorb()
        return ie

    def tab_forward(self):
        selected_pane = None
        selected_index = 0
        for i in range(0, len(self.chain_order)):
            if self.chain_order[i]._focus is True:
                selected_pane = self.chain_order[i]
                selected_index = i
                break

        if selected_pane is None:
            self.chain_order[0].focus()
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
        return True

    def tab_back(self):
        selected_pane = None
        selected_index = 0
        for i in range(0, len(self.chain_order)):
            if self.chain_order[i]._focus is True:
                selected_pane = self.chain_order[i]
                selected_index = i
                break

        if selected_pane is None:
            self.chain_order[0].focus()
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
        return True

# class Screen_Title(object):
#     def __init__(self, stdscr, height, width, y, x, title, no_title=False, draw_lower=False, lower_y=-1):
#         # raise Exception('here')
#         super(Screen_Title, self).__init__()
#         self._stdscr = stdscr
#         self._height = height
#         self._width = width
#         self._y = y
#         self._x = x
#         self._lower_y = lower_y
#         if self._lower_y != -1:
#             self._draw_lower = draw_lower
#             self._lower_line = '─'*(self._width-2)
#         else:
#             self._draw_lower = False

#         if no_title:
#             self._title = ''
#         else:
#             self._title = ' ' + title + ' '
#         self._fillerl = ''.ljust(math.ceil((self._width-2)/2 - len(self._title)/2), '─')
#         self._fillerr = ''.ljust(math.floor((self._width-2)/2 - len(self._title)/2), '─')

#         self._win = self._stdscr.derwin(self._height, self._width, self._y, self._x)

#         if self._draw_lower:
#             self._lower_win = self._stdscr.derwin(self._height, self._width, self._lower_y, self._x)

#     def draw(self):
#         try:
#             self._win.addstr(0, 1, self._fillerl, curses.color_pair(2))
#             self._win.addstr(0, 1 + len(self._fillerl), self._title, curses.color_pair(1))
#             self._win.addstr(0, 1 + len(self._fillerl) + len(self._title), self._fillerr, curses.color_pair(2))
#             self._win.refresh()

#             if self._draw_lower:
#                 self._lower_win.addstr(0, 1, self._lower_line, curses.color_pair(2))
#                 self._lower_win.refresh()
#         except curses.error:
#             pass

class Layout(core.Processable):
    def __init__(self, title=None):
        super(Layout, self).__init__()

        self._panes = []
        self._footer = None
        self._tab_order = None
        self._title_text = title

    def set_size(self, x_divs, y_divs):
        self._x_divs = x_divs
        self._y_divs = y_divs

    def assign_win(self, win):
        self._stdscr = win
        self.process_resize(init=True)

    def calc_per_block(self, height_reduction=0, width_reduction=1):
        self._y_per_block = math.floor((self._h - height_reduction) / self._y_divs)
        self._x_per_block = math.floor((self._w - width_reduction) / self._x_divs)

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

    def assign_footer(self, footer):
        self._footer = core.Pane_Holder(footer, 0, 0, 0, 0)

    def add_tab_order(self, tab_order):
        self._tab_order = tab_order

    def add_pane(self, pane, start_x, start_y, width, height, one_line=False, fixed_to=None):
        ph = core.Pane_Holder(pane, start_x, start_y, width, height, one_line=one_line, fixed_to=fixed_to, unfocus_callback=self.unfocus_all)
        self._panes.append(ph)

    def calculate_all_pane_windows(self):

        if self._footer is not None:
            win = self._stdscr.derwin(1, self._w, self._h - 1, 0)
            self._footer.link_win(win)
            self._h = self._h - 1

            self.calc_per_block(height_reduction=1)

        for ph in self._panes:
            new_win = self.calculate_win_for_pane(ph)
            ph.link_win(new_win)
        if len(self._panes) > 0:
            self._panes[0].get_pane().focus()

    def calculate_win_for_pane(self, ph):
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

        # if y > 0:
        #     y_shift = -1

        if x > 0:
            x_shift = 0

        if ph.get_is_one_line():
            #                         nlines,      ncols,                           begin_y,                                          begin_x
            win = self._stdscr.derwin(1 - y_shift, w * self._x_per_block - x_shift, y * self._y_per_block + self._y_offset + y_shift, x * self._x_per_block+x_shift)
        else:
            nlines = h * self._y_per_block - y_shift
            ncols = w * self._x_per_block - x_shift
            begin_y = y * self._y_per_block + self._y_offset + y_shift
            begin_x = x * self._x_per_block+x_shift
            if y == self._y_divs - 1:
                # This pane is on the last row. We should make sure it actually expands all the way to the bottom
                if begin_y + nlines < self._h:
                    nlines = self._h - begin_y

            if x == self._x_divs - 1:
                # This pane is on the last col. We should make sure it actually expands all the way to the right
                if begin_x + ncols < self._w:
                    ncols = self._w - begin_x

            
            win = self._stdscr.derwin(nlines, ncols, begin_y, begin_x)

        return win

    def focus_default(self):
        if len(self._panes) > 0:
            self._panes[0].get_pane().focus()

    # def move_focus(self, x_amt, y_amt):
    #     (x, y) = self.current_focus
    #     old_pane = self._pane_order[y][x]
    #     y_lim = len(self._pane_order)
    #     x_lim = len(self._pane_order[0])
    #     wrap_limiter = 2
    #     if (x_amt == 0 and y_amt == 0) or (x_amt != 0 and y_amt != 0):
    #         raise Exception(f'Invalid step: {(x_amt, y_amt)}')

    #     while (self._pane_order[y][x] == None or self._pane_order[y][x] == old_pane) and wrap_limiter > 0:
    #         if x_amt != 0:
    #             # move by x
    #             x = x + x_amt
    #         else:
    #             # move by y
    #             y = y + y_amt
            
    #         if x < 0:
    #             x = 0
    #             wrap_limiter = wrap_limiter - 1
    #         elif x > x_lim - 1:
    #             x = x_lim  - 1
    #             wrap_limiter = wrap_limiter - 1

    #         if y < 0:
    #             y = 0
    #             wrap_limiter = wrap_limiter - 1
    #         elif y > y_lim  - 1:
    #             y = y_lim  - 1
    #             wrap_limiter = wrap_limiter - 1


    #     if wrap_limiter == 0:
    #         # raise Exception(f'Wrapped {(x, y)}:{self._pane_order[y][x]}')
    #         return
    #     self.current_focus = (x, y)
    #     self.set_focus()

    def key_input(self, ie):
        tmp_ie = ie
        for p in self._panes:  # Process direct focus keys
            tmp_ie = p.key_input(tmp_ie)
            if tmp_ie.key is None:
                return tmp_ie

        if self._tab_order is not None:
            tmp_ie = self._tab_order.key_input(tmp_ie)

        # if ie.key == 259:  # Up Arrow
        #     self.move_focus(0, -1)
        # elif ie.key == 258:  # Down Arrow
        #     self.move_focus(0, 1)
        # elif ie.key == 261:  # Right Arrow
        #     self.move_focus(1, 0)
        # elif ie.key == 260:  # Left Arrow
        #     self.move_focus(-1, 0)
        # else:
        return tmp_ie

        # tmp_ie.absorb()
        # return tmp_ie

    def get_focused_pane(self):
        for p in self._panes:
            if p.get_pane().get_focus() is True:
                return p.get_pane()
        return None

    def process_resize(self, init=False):
        self._h, self._w = self._stdscr.getmaxyx()

        # self._pane_order_x_len = self._w
        # self._pane_order_y_len = self._h
        # self._pane_y_offset = -1
        # self._pane_order = [[None]*self._pane_order_x_len for _ in range(self._pane_order_y_len-1)]

        self._y_offset = 0

        # # raise Exception(self._title_text)
        # if self._title_text is not None and self._frameless is not True:
        #     self._Screen_Title = Screen_Title(self._stdscr, 1, self._w, 0, 0, self._title_text, draw_lower=True, lower_y=self._h-1)
        #     self._h = self._h - 2
        #     self._y_offset = 1
        # else:
        #     self._Screen_Title = None
            

        self.calc_per_block()

        if not init: # This is a resize that happened after the creation of the window
            # Save the current focused pane

            last_focused_object = self.get_focused_pane()
            self.unfocus_all()

            # Resize each pane:
            for ph in self._panes:
                new_win = self.calculate_win_for_pane(ph)
                ph.link_win(new_win)

            for ph in self._panes:
                ph.get_pane().window_size_update()

            # self.set_focus_location_from_object(last_focused_object)
            last_focused_object.focus()

            for p in self._panes:
                p.get_pane().needs_drawing()
                p.get_pane().clear()

class Screen(object):
    def __init__(self, stdscr, exit_key='q', process_rate_ps=30, frame_rate_ps=15, sub_screen=False):
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

        self._recent_resize = False
        self._resize_draw_frame_counter = 0

        self._is_sub_screen = sub_screen

        self._layout = None

    def external_exit(self):
        self._force_close = True

    def build(self, layout):
        if self._layout is not None:
            raise Exception('Screen already has a layout object')
        self._layout = layout
        if self._layout._tab_order is None:
            panes = self._layout._panes
            p_list = []
            for p in panes:
                p_list.append(p.get_pane())
            self._layout.add_tab_order(Tab_Chain(*p_list, wrap=(not self._is_sub_screen)))

        self._layout.calculate_all_pane_windows()


        for pane in layout.get_panes():
            pane_obj = pane.get_pane()
            if isinstance(pane_obj, core.Drawable):
                self.drawable_objects.append(pane_obj)
            elif isinstance(pane_obj, core.Processable):
                self.processable_objects.append(pane_obj)


        for p in self.processable_objects:
            if isinstance(p, core.Init):
                p.init()
        for d in self.drawable_objects:
            if isinstance(d, core.Init):
                d.init()

    def add_processable_objects(self, *obj):
        for o in obj:
            self.processable_objects.append(o)

    def add_drawable_objects(self, *obj):
        for o in obj:
            self.drawable_objects.append(o)

    def add_drawable_object_to_begining_of_queue(self, obj):
        self.drawable_objects.insert(0, obj)

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


        #TODO: Try using get_wch to see if we can capture more complex key inputs
        #TODO: Support mouse scrolling
        c = self._stdscr.getch()
        
        self._ie = Input_Event(c)

        if c != -1:
            curses.flushinp()

        if self._ie is not None and self._ie.key == self._exit_key:
            return False

        self._ie = self.key_input(self._ie)

        self.process(current_time)
        self.draw(time=current_time)
        
        self._last_action_time = current_time
        return True

    def process_resize(self):
        self._layout.process_resize()
        self._recent_resize = True
        self._resize_draw_frame_counter = 0

    def key_input(self, ie):
        tmp_ie = ie
        if ie.key == curses.KEY_RESIZE:
            #TODO: Implement resize code
            self.process_resize()
        else:
            for p in self.processable_objects:
                tmp_ie = p.key_input(tmp_ie)
            for d in self.drawable_objects:
                tmp_ie = d.key_input(tmp_ie)
            
            tmp_ie = self._layout.key_input(tmp_ie)

        return tmp_ie

    def force_needs_drawing(self):
        for d in self.drawable_objects:
            d.needs_drawing()

    def process(self, current_time):
        for p in self.processable_objects:
            p.process(current_time)
        for d in self.drawable_objects:
            d.process(current_time)
        self._last_process_time = current_time

    def draw(self, time=None):
        if self._recent_resize is True:
            self._resize_draw_frame_counter = self._resize_draw_frame_counter + 1
            if self._resize_draw_frame_counter > 10:
                for d in self.drawable_objects:
                    if isinstance(d, core.Pane):
                        d.needs_drawing()
                self._resize_draw_frame_counter = 0
                self._recent_resize = False
            else:
                self._last_draw_time = time
                return

        for d in self.drawable_objects:
            if not d.get_awaiting_window_update():
                d.draw()

        self._last_draw_time = time


