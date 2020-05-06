import curses
import math
import time
import copy
from enum import Enum

from tinywin import core

class Scroll_Area(object):
    """Scroll Area calculation helper object

    This class aids in the calculation of a scroll area. Lines are passed to
    the object, as well as width and height constraints. Either a selected
    line index or forced scroll command can be used to scroll the contents.
    The results can be retrieved and used to draw the scroll area with the
    correct lines in view.
    """

    def __init__(self, height, width, current_cursor=0, force_scrolling_only=False, lines=None):
        self.mouse_y_offset = 0
        self._org_lines = lines
        self.init_layout(height, width, current_cursor)
        self._scroll_value = 0
        self._force_scrolling_only = force_scrolling_only
        self._org_width = width

    def set_force_scrolling_only(self, force_scrolling_only):
        self._force_scrolling_only = force_scrolling_only

    def update_lines(self, lines, update_org_width=False):
        self._org_lines = lines
        self.init_layout(self._height, self._org_width, 0, update_org_width=update_org_width)

    def init_layout(self, height, width, current_cursor, update_org_width=True):
        """Calculate scrollbar layout information based upon the input pane dimensions"""
        if self._org_lines is None:
            return
        self._height = height
        self._width = width
        if update_org_width:
            self._org_width = width
        self._current_cursor = current_cursor
        self._first_index = 0
        self.scroll_bar = []
        self._scroll_value = 0

        # Calculate whether or not the scroll bar will be needed
        self.scroll_bar_needed = True if len(self._org_lines) >= self._height else False

        # If the scroll bar is needed, reduce the width to account for it
        if self.scroll_bar_needed:
            self._width = self._width - 1
            for _ in range(0, self._height - 1):
                self.scroll_bar.append(False)

        # Trim the lines so they fit horizontally in the pane. If they are too lone, add '...' and cut off the end.
        self._trimmed_lines = []
        self._lines = []
        for l in self._org_lines:
            l.shorten_to_length(self._width)
            # l.data['selected'] = False
            self._lines.append(l)

        if self._lines:
            # Mark the approperate line as selected

            # # Open a file with access mode 'a'
            # with open("Output2.txt", "a") as file_object:
            #     print('> 1: ', end='', file=file_object)
            #     for l in self._lines:
            #         print(str(l.data), file=file_object, end = ', ')
            #     print('', file=file_object)

            self._lines[current_cursor].data['cursor'] = True

            # with open("Output2.txt", "a") as file_object:
            #     print('> 2: ', end='', file=file_object)
            #     for l in self._lines:
            #         print(str(l.data), file=file_object, end = ', ')
            #     print('', file=file_object)

        # Calculate the total number of lines that can fit in this scroll area
        self.total_num_lines = len(self._lines)

    def cursor(self, selection):
        """Sets the current line selection"""
        # Remove the old selection
        self._lines[self._current_cursor].data['cursor'] = False
        # Assign and mark the current selection
        self._current_cursor = selection
        if self._current_cursor < 0:
            self._current_cursor = 0
        elif self._current_cursor > len(self._lines) - 1:
            self._current_cursor = len(self._lines) - 1
        self._lines[self._current_cursor].data['cursor'] = True

    def get_first_index(self):
        """Get the first index in lines which should appear in the scroll area"""
        if self._trimmed_lines is None:
            self.calculate_trimmed_lines()
        return self._first_index

    def get_trimmed_lines(self):
        """Get the list of lines to be drawn to the scroll area"""
        if self._trimmed_lines is None:
            self.calculate_trimmed_lines()
        return self._trimmed_lines

    def get_lines(self):
        return self._org_lines

    def get_scroll_bar(self):
        """Get the scroll bar list, if applicable"""
        return self.scroll_bar if self.scroll_bar_needed else None

    def scroll_by(self, scroll_value):
        """Force a scroll of a certain amount. Useful for non-selectable lists."""

        if self.scroll_bar_needed:
            proposed_val = self._scroll_value + scroll_value
            if self._first_index == 0 and scroll_value < 0:
                return False
            if self._first_index == self.total_num_lines - (self._height - 1) and scroll_value > 0:
                return False

            self._scroll_value = proposed_val
            return True
        else:
            return False

    def calculate_trimmed_lines(self):
        """Calculate the lines that can be displayed in the scroll area"""
        # Check if we will need to use the scroll bar
        if self.scroll_bar_needed:
            # The scroll bar is needed. We'll have to reduce the data to get it to
            # fit in the scroll area

            # Get the current scroll area min and max lines
            min_value_on_screen = self._first_index
            max_value_on_screen = self._height + self._first_index - 2

            # Check to see if we need to scroll up or down, based on the current
            # selected line
            if self._scroll_value == 0 and not self._force_scrolling_only:
                # The user hasn't forced scrolling. We can infer it based on the selected item
                if self._current_cursor > max_value_on_screen:
                    self._first_index = self._current_cursor - self._height + 2
                elif self._current_cursor < min_value_on_screen:
                    self._first_index = self._current_cursor
            else:
                # The user has forced a scroll amount
                self._first_index = self._first_index + self._scroll_value
                # Restrict the index from going out of bounds
                if self._first_index < 0:
                    self._first_index = 0
                elif self._first_index > self.total_num_lines - (self._height - 1):
                    self._first_index = self.total_num_lines - (self._height - 1)
                self._scroll_value = 0

            # Wrap the starting index of the device list
            if self._first_index < 0:
                self._first_index = 0
            elif self._first_index > len(self._lines) - self._height + 1:
                self._first_index = len(self._lines) - self._height + 1

            # Set the mouse offset and produce the trimmed line output
            self.mouse_y_offset = self._first_index
            self._trimmed_lines = self._lines[self._first_index:self._first_index + self._height - 1]

            ##### Scroll Bar Calculations #####
            # Calculate the total lines on the screen
            lines_on_screen = self._height - 1

            # Clear the scroll bar array
            for i in range(0, len(self.scroll_bar)):
                self.scroll_bar[i] = False

            # Calculate the scroll bar height and position, based on the lines showing on screen
            scroll_bar_height = math.floor((lines_on_screen * lines_on_screen) / self.total_num_lines)
            scroll_bar_pos = math.floor((self._first_index+1) * (lines_on_screen / self.total_num_lines))

            # Configure the scroll bar so it always shows the right position at the top and bottom
            if self._first_index == 0:
                # Scroll bar is at the begining
                for i in range(0, scroll_bar_height):
                    self.scroll_bar[i] = True
            elif self._first_index + lines_on_screen == self.total_num_lines:
                # Scroll bar is at the end
                for i in range(lines_on_screen - scroll_bar_height, lines_on_screen):
                    self.scroll_bar[i] = True
            else:
                # Scroll bar is somewhere in the middle
                for i in range(scroll_bar_pos, scroll_bar_pos+scroll_bar_height):
                    self.scroll_bar[i] = True
        else:
            # No scroll bar, just return the original line data unaltered
            self.mouse_y_offset = 0
            self._trimmed_lines = self._lines

class Scroll_Pane_Type(Enum):
    READ_ONLY = 1
    CURSOR_ONLY = 2
    SINGLE_SELECT = 3
    MULTI_SELECT = 4

class Scroll_Pane(core.Pane):
    def __init__(self, stdscr, scroll_type):
        super(Scroll_Pane, self).__init__(stdscr)

        self._scroll_type = scroll_type

        self._overall_width_reduction = self.border_width_reduction

        self._header_line = None
        self._scroll_contents = None

        if self._scroll_type == Scroll_Pane_Type.READ_ONLY:
            self._overall_width_reduction = math.ceil(self.border_width_reduction / 2)
        elif self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT or self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            self.cursor_symbol = '>'
            self.cursor_no_symbol = ' '
            self._cursor = 0
            self._selection_width_reduction = len(self.cursor_symbol)
        else:
            raise ValueError(f'Unimplemented scroll type "{self._scroll_type}"')

        self.scroll_area = None

    def set_header_line(self, header_line):
        self._header_line = header_line
        if self._header_line is None:
            return

    def set_contents(self, contents):
        self._scroll_contents = contents
        self.z = len(contents)
        self._num_options = self.z

        for i in range(0, len(self._scroll_contents)):
            if isinstance(self._scroll_contents[i], str):
                self._scroll_contents[i] = core.Text_Line(self._scroll_contents[i], None)
            self._scroll_contents[i].data['cursor'] = False
            self._scroll_contents[i].data['selected'] = False

        if self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT or self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            self.num_pad_len = len(str(self.z))
            self.num_pad_len_width = self.num_pad_len + 2
            self._overall_width_reduction = self.border_width_reduction - self._selection_width_reduction - self.num_pad_len_width
        if self.scroll_area is not None:
            self.scroll_area.update_lines(self._scroll_contents)
            if self._cursor is not None:
                self.scroll_area.cursor(self._cursor)
        self.needs_drawing()

    def get_contents(self):
        return self._scroll_contents

    def assign_win(self, win):
        super(Scroll_Pane, self).assign_win(win)

        # if len(self.title) + self.border_width_reduction > self._w:
        #     raise TerminalTooSmallError

        if self._scroll_contents is None:
            self.scroll_area = Scroll_Area(self._h - self.border_height_reduction,
                                           self._w - self._overall_width_reduction)
        else:
            self.scroll_area = Scroll_Area(self._h - self.border_height_reduction,
                                           self._w - self._overall_width_reduction,
                                           lines=self._scroll_contents)

        if self._scroll_type == Scroll_Pane_Type.READ_ONLY:
            self.scroll_area.set_force_scrolling_only(True)

    def step_by(self, step, ie):
        end_stop = False
        if self._scroll_type == Scroll_Pane_Type.READ_ONLY:
            end_stop = not self.scroll_area.scroll_by(step)
        elif self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT or self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            cur = self._cursor + step
            if cur < 0:
                cur = 0
                end_stop = True
            elif cur > self._num_options - 1:
                cur = self._num_options - 1
                end_stop = True
            self.cursor(cur)
            self.needs_drawing()
        else:
            raise ValueError(f'Unimplemented scroll type "{self._scroll_type}"')

        if not end_stop:
            ie.absorb()
            if step != 0:
                self.needs_drawing()
        return ie

    def key_input(self, input_event):
        input_event = super(Scroll_Pane, self).key_input(input_event)
        key = input_event.key
        if key is None or self._focus == False:
            return input_event
        if key == 258:  # Down Arrow
            return self.step_by(1, input_event)
        elif key == 336:  # Shift-Down Arrow
            return self.step_by(5, input_event)
        elif key == 259:  # Up Arrow
            return self.step_by(-1, input_event)
        elif key == 337:  # Shift-Up Arrow
            return self.step_by(-5, input_event)
        elif key == 32:  # Space
            return self.selection_event(input_event)
        elif key == 43:  # Plus
            return self.selection_event(input_event, force_to_value=True)
        elif key == 45 or key == 95:  # Minus or underline
            return self.selection_event(input_event, force_to_value=False)
        elif key == curses.KEY_MOUSE:
            try:
                _, self._mx, self._my, _, _ = input_event.get_mouse()
                offset_y, _ = self._win.getbegyx()
                self.cursor(self._my - offset_y - math.ceil(self.border_height_reduction / 2) + self.scroll_area.mouse_y_offset)
            except curses.error:
                pass
            input_event.absorb()
        else:
            return input_event  # Unknown key - pass it back to the driver

        input_event.absorb()

        return input_event

    def selection_event(self, input_event, force_to_value=None):
        if force_to_value is not None and (self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT):
            if force_to_value is True:
                for l in self.scroll_area.get_lines():
                    l.data['selected'] = True
            else:
                for l in self.scroll_area.get_lines():
                    l.data['selected'] = False
            self.needs_drawing()
            input_event.absorb()
            return input_event
        if self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT:
            self.select(self._cursor)
            input_event.absorb()
            return input_event
        elif self._scroll_type == Scroll_Pane_Type.MULTI_SELECT:
            self.select(self._cursor, clear=False)
            input_event.absorb()
            return input_event
        elif self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            return input_event
        else:
            raise ValueError(f'Unimplemented scroll type "{self._scroll_type}"')
        return input_event

    def select(self, selection, clear=True):
        if clear:
            for l in self.scroll_area.get_lines():
                l.data['selected'] = False
            self.scroll_area.get_lines()[selection].data['selected'] = True
        else:
            self.scroll_area.get_lines()[selection].data['selected'] = not self.scroll_area.get_lines()[selection].data['selected']
        self.needs_drawing()

    def cursor(self, cursor):
        self._cursor = cursor
        self.scroll_area.cursor(self._cursor)

    def get_cursor(self):
        return self._cursor

    def get_selected(self):
        if self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT:
            lines = self.scroll_area.get_lines()
            for i in range(0, len(lines)):
                if lines[i].data['selected'] is True:
                    return i
            return -1
        elif self._scroll_type == Scroll_Pane_Type.MULTI_SELECT:
            lines = self.scroll_area.get_lines()
            selected_indices = []
            for i in range(0, len(lines)):
                if lines[i].data['selected'] is True:
                    selected_indices.append(i)
            return selected_indices
        else:
            return None

    def process(self, process_time):
        super(Scroll_Pane, self).process(process_time)

    def draw(self):
        if not self.get_needs_drawing():
            return
        self.init_frame(title='', unfocused_line_color=curses.color_pair(2))

        self.scroll_area.calculate_trimmed_lines()
        lines = self.scroll_area.get_trimmed_lines()
        index = self.scroll_area.get_first_index()
        scroll = self.scroll_area.get_scroll_bar()
        screen_index = 0
        if self._scroll_type == Scroll_Pane_Type.READ_ONLY:
            for l in lines:
                l.output_to_window(self._win, self.line_counter, self._overall_width_reduction)
                if scroll is not None:
                    if not scroll[screen_index]:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(2), inc=False)
                    else:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(1), inc=False)
                self.inc()
                index = index + 1
                screen_index = screen_index + 1
        elif self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT or self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            for l in lines:
                c = l.data['cursor']
                s = l.data['selected']

                selected_color_mod = curses.A_REVERSE if s else 0

                self.addstr_auto(0, self.cursor_symbol if c else self.cursor_no_symbol, curses.color_pair(1) | selected_color_mod, inc=False)

                self.addstr_auto(len(self.cursor_symbol), (str(index)+':').ljust(self.num_pad_len_width, ' '), curses.color_pair(1) | selected_color_mod, inc=False)

                l.output_to_window(self._win, self.line_counter, len(self.cursor_symbol)+self.num_pad_len_width+2, highlight=selected_color_mod)
                # self.addstr_auto(len(self.cursor_symbol)+self.num_pad_len_width, str(l), inc=False)
                if scroll is not None:
                    if not scroll[screen_index]:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(2), inc=False)
                    else:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(1), inc=False)
                self.inc()
                index = index + 1
                screen_index = screen_index + 1
        else:
            raise ValueError(f'Unimplemented scroll type "{self._scroll_type}"')

        super(Scroll_Pane, self).draw()

class Notification_Box(core.Pane):
    def __init__(self, stdscr, x=0, y=0, header='', right_aligned=False, loading_square=True, idle=True):
        super(Notification_Box, self).__init__(stdscr)
        self._notification_start_time = -1
        self._notification_timeout = -1
        self._notification_text = ''
        self._loading_square = loading_square
        self._loading_square_done = idle
        self._loading_animation = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        self._loading_animation_done = '⠿'
        self._loading_animation_index = 0
        self._loading_animation_length = len(self._loading_animation)
        self._loading_time_between_frames = 0.1
        self._loading_time_of_last_frame = -1
        self._x = x
        self._y = y
        self._clear = False
        self._last_text = ''
        self._header = header
        self._right_aligned = right_aligned
        self.needs_drawing()

    def assign_win(self, win):
        super(Notification_Box, self).assign_win(win)

    def get_max_message_length(self, using_loading_square=False):
        if not self.win_has_been_assigned:
            return None
        if using_loading_square:
            return self._w - len(self._header) - len(self._loading_animation_done) - self._x - self.border_width_reduction
        else:
            return self._w - len(self._header) - self._x

    def key_input(self, input_event):
        input_event = super(Notification_Box, self).key_input(input_event)
        return input_event

    def process(self, time):
        if self._notification_timeout != -1 and time > self._notification_timeout:
            self._notification_start_time = -1
            self._notification_timeout = -1
            self._notification_text = ''
            self._clear = True
            self.needs_drawing()
        elif self._loading_square:
            cur_time = time
            if cur_time - self._loading_time_of_last_frame >= self._loading_time_between_frames:
                self.needs_drawing()
                self._loading_time_of_last_frame = cur_time

    def inc_animation(self):
        self._loading_animation_index = self._loading_animation_index + 1
        if self._loading_animation_index > self._loading_animation_length - 1:
            self._loading_animation_index = 0

    def draw(self, force=False):
        if not self.get_needs_drawing() and force is False and self._clear is False:
            return

        if self._clear:
            self._clear = False
            if self._right_aligned:
                # raise Exception('Not implemented')
                pass
            else:
                self._win.move(self._y, self._x)
                self._win.clrtoeol()
                self._win.addstr(self._header, curses.color_pair(1))
        else:
            ani = ''
            if self._loading_square:
                if self._loading_square_done:
                    ani = self._loading_animation_done + ' '
                else:
                    ani = self._loading_animation[self._loading_animation_index] + ' '
                    self.inc_animation()

            header = ani + self._header
            text = self._notification_text
            x = self._x
            if self._right_aligned:
                x = self._x - (len(text) + len(header))
                self._win.addstr(self._y, self._x - len(self._last_text), ' ' * len(self._last_text))
            else:
                self.init_frame(single_line=True, single_line_x=self._x, single_line_y=self._y)

            if isinstance(text, core.Text_Line):
                self._win.addstr(self._y, x, header)
                text.output_to_window(self._win, self._y, x + len(header))
            else:
                self._win.addstr(self._y, x, header + text)
            self._last_text = header + text
            super(Notification_Box, self).draw()

    def notify(self, notification, notification_duration=2, loading_square=False, loading_square_done=False):
        self._notification_text = notification
        if notification_duration == -1:  # -1 indicates forever
            self._notification_start_time = -1
            self._notification_timeout = -1
        else:
            self._notification_start_time = time.time()
            self._notification_timeout = self._notification_start_time + notification_duration
        self._loading_square = loading_square
        self._loading_square_done = loading_square_done
        self.needs_drawing()

class Menu_Pane(core.Pane):
    def __init__(self, stdscr, *args, subtle=False):
        super(Menu_Pane, self).__init__(stdscr)
        self._menu_items = []
        self._selected_menu_item = -1
        self._last_selected_menu_item = -1
        self._subtle = subtle
        for a in args:
            self._menu_items.append(a)

    def __str__(self):
        return 'M'

    def assign_win(self, win):
        super(Menu_Pane, self).assign_win(win)
        self.calculate_menu_locations()

    def focus(self):
        self._selected_menu_item = self._last_selected_menu_item if self._last_selected_menu_item != -1 else 0
        self._menu_items[self._selected_menu_item].select(True)
        super(Menu_Pane, self).focus()

    def unfocus(self):
        self._menu_items[self._selected_menu_item].select(False)
        self._selected_menu_item = -1
        super(Menu_Pane, self).unfocus()

    def set_focus(self, val):
        if val:
            self.focus()
        else:
            self.unfocus()

    def move_menu_cursor(self, step, input_event):
        self._selected_menu_item = self._selected_menu_item + step
        end_stop = False
        if self._selected_menu_item < 0:
            self._selected_menu_item = 0
            end_stop = True
        elif self._selected_menu_item > len(self._menu_items) - 1:
            self._selected_menu_item = len(self._menu_items) - 1
            end_stop = True

        for m in self._menu_items:
            m.select(False)
        self._menu_items[self._selected_menu_item].select(True)

        self.needs_drawing()

        if not end_stop:
            input_event.absorb()
            self._last_selected_menu_item = self._selected_menu_item
        return input_event

    def click_menu_item(self, input_event):
        item = self._menu_items[self._selected_menu_item]
        if item.click():
            input_event.absorb()

        return input_event

    def check_menu_hotkeys(self, input_event):
        for m in self._menu_items:
            input_event = m.key_input(input_event)

        return input_event

    def key_input(self, input_event):
        input_event = super(Menu_Pane, self).key_input(input_event)
        key = input_event.key
        if key is None or self._focus == False:
            input_event = self.check_menu_hotkeys(input_event)
            return input_event
        if key == 261:  # Right Arrow
            return self.move_menu_cursor(1, input_event)
        elif key == 260:  # Left Arrow
            return self.move_menu_cursor(-1, input_event)
        elif key == 10 or key == 32:  # Enter key or space key
            return self.click_menu_item(input_event)
        else:
            input_event = self.check_menu_hotkeys(input_event)
            return input_event  # Unknown key - pass it back to the driver

        input_event.absorb()

        return input_event

    def calculate_menu_locations(self):
        divisor = math.ceil(self._w / (len(self._menu_items) + 1))
        current_x = divisor
        if self._subtle:
            current_y = 1
        else:
            current_y = math.floor(self._h / 2) - 1
        for m in self._menu_items:
            m.set_center(current_x, current_y)
            current_x = current_x + divisor

    def draw(self):
        if not self.get_needs_drawing():
            return
        if self._subtle:
            self.init_frame(title='Menu', omit_border=True, border_color=curses.color_pair(1), unfocused_line_color=curses.color_pair(2))
        else:
            self.init_frame(title='Menu')

        for m in self._menu_items:
            m.draw(self._win)

        super(Menu_Pane, self).draw()
