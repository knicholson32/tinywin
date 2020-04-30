import curses
import math
import time
import json
import subprocess
import copy
import threading
from enum import Enum

from panes import Pane, PaneError, Processable, Init

class Text_Wrapper(object):
    def __init__(self, text, color):
        self.text = text
        self.color = color

    def __len__(self):
        return len(self.text)

    def copy(self):
        return Text_Wrapper(self.text, self.color)

class Text_Line(object):
    def __init__(self, *args, data=None, ellipsis_color=None, ellipsis_text='...', allowed_width=None):
        self.data = data
        if self.data is None:
            self.data = dict()
        if ellipsis_color is None:
            try:
                self._ellipsis_color = curses.color_pair(2)
            except curses.error:
                self._ellipsis_color = None
        else:
            self._ellipsis_color = ellipsis_color
        self._ellipsis_text = ellipsis_text
        texts = []
        colors = []
        current_arg_is_text = True
        for arg in args:
            if current_arg_is_text:
                if isinstance(arg, Text_Line):
                    texts.append(str(arg))
                else:
                    texts.append(arg)
            else:
                colors.append(arg)
            current_arg_is_text = not current_arg_is_text

        self._text_objects = []
        self._shortened_text_objects = []

        for i in range(0, len(texts)):
            self._text_objects.append(Text_Wrapper(texts[i], colors[i]))

        if allowed_width is None:
            self._allowed_width = 0
            for t in self._text_objects:
                self._allowed_width = self._allowed_width + len(t)
        else:
            self._allowed_width = allowed_width

        self._shortened_text_objects = self._text_objects

    def get_data(self):
        return self.data

    def set_data(self, data):
        self.data = data.copy()

    def set_allowed_width(self, width):
        self._allowed_width = width

    def get_text_component(self, index):
        return self._text_objects[index]

    def output_to_window(self, win, line_counter, x_offset, highlight=0):
        len_counter = 0
        for t in self._shortened_text_objects:
            if not highlight:
                win.addstr(line_counter, len_counter + x_offset, t.text, t.color)
            else:
                win.addstr(line_counter, len_counter + x_offset, t.text, t.color | highlight)
            len_counter = len_counter + len(t)
        if highlight:
            win.addstr(line_counter, len_counter + x_offset, ' '*(self._allowed_width - len_counter - x_offset - 3), highlight)
        return len_counter

    def __len__(self, use_unshortened_text=False):
        counter = 0
        if use_unshortened_text is True:
            for t in self._text_objects:
                counter = counter + len(t)
        else:
            for t in self._shortened_text_objects:
                counter = counter + len(t)
        return counter

    def __add__(self, o):
        return self.__str__() + o

    def __radd__(self, o):
        return o + self.__str__()

    def __str__(self, use_unshortened_text=False):
        string = ''
        if use_unshortened_text is True:
            for t in self._text_objects:
                string = string + t.text
        else:
            for t in self._shortened_text_objects:
                string = string + t.text
        return string

    def uniform_color(self, color):
        for t in self._text_objects:
            t.color = color

        for t in self._shortened_text_objects:
            t.color = color

    def shorten_to_length(self, length):
        self._allowed_width = length
        tmp_shortened_text_objects = []
        for t in self._text_objects:
            tmp_shortened_text_objects.append(t.copy())
        total_len = 0
        for t in tmp_shortened_text_objects:
            total_len = total_len + len(t)
        if total_len > length:
            self._shortened_text_objects = []
            # print(total_len, length)
            index = len(tmp_shortened_text_objects) - 1  # Start at the end of the colored string
            character_index = len(tmp_shortened_text_objects[index])-1  # Start at the last character in the last string
            removing = True

            while removing is True:
                total_len = total_len - 1
                character_index = character_index - 1
                if character_index < 0:
                    index = index - 1
                    if index < 0:
                        raise TerminalTooSmallError(f'Cannot shorten text "{self.__str__(use_unshortened_text=True)}" to length "{length}"')
                    character_index = len(tmp_shortened_text_objects[index])-1
                if total_len + len(self._ellipsis_text) <= length:
                    removing = False

            # We can use all text up to index, and the last piece of text can be used up to the character_index

            tmp_shortened_text_objects[index].text = tmp_shortened_text_objects[index].text[0:character_index+1]  # Shorten last index text
            if tmp_shortened_text_objects[index].text[len(tmp_shortened_text_objects[index].text)-1] == ' ':  # Trim a space if one exists
                tmp_shortened_text_objects[index].text = tmp_shortened_text_objects[index].text[:-1]

            for i in range(0, index+1):
                self._shortened_text_objects.append(tmp_shortened_text_objects[i])
            self._shortened_text_objects.append(Text_Wrapper(self._ellipsis_text, self._ellipsis_color))

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

class Scroll_Pane(Pane):
    def __init__(self, stdscr, scroll_type):
        super(Scroll_Pane, self).__init__(stdscr)

        self._scroll_type = scroll_type

        self._overall_width_reduction = self.border_width_reduction

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

    def set_contents(self, contents):
        self._scroll_contents = contents
        self.z = len(contents)
        self._num_options = self.z

        for i in range(0, len(self._scroll_contents)):
            self._scroll_contents[i].data['cursor'] = False
            self._scroll_contents[i].data['selected'] = False


        if self._scroll_type == Scroll_Pane_Type.SINGLE_SELECT or self._scroll_type == Scroll_Pane_Type.MULTI_SELECT or self._scroll_type == Scroll_Pane_Type.CURSOR_ONLY:
            self.num_pad_len = len(str(self.z))
            self.num_pad_len_width = self.num_pad_len + 2
            self._overall_width_reduction = self.border_width_reduction - self._selection_width_reduction - self.num_pad_len_width
        if self.scroll_area is not None:
            self.scroll_area.update_lines(self._scroll_contents)

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

class TerminalTooSmallError(PaneError):
    def __init__(self, msg='Terminal too small for application'):
        super(TerminalTooSmallError, self).__init__(msg)

class FQBN_Board_Details(Pane):
    def __init__(self, stdscr, devices, data_loader, board_list_obj, notification_pane=None):
        super(FQBN_Board_Details, self).__init__(stdscr)
        self.title = 'Board Details'
        self.notification_pane = notification_pane
        self.devices = devices
        self.data_loader = data_loader
        self._board_list_obj = board_list_obj
        self._selected_index = -1
        self.data = {}
        self.current_selection_unloaded = True
        self._selection = -1
        self._num_options = -1

        # self.local_notifications.notify('Testing', notification_duration=5)

        self._lines = []

    def __str__(self):
        return 'D'

    def assign_win(self, win):
        super(FQBN_Board_Details, self).assign_win(win)
        self.scroll_area = Scroll_Area(self._h - self.border_height_reduction, self._w - self.border_width_reduction, 0, force_scrolling_only=True, lines=[])

    def step_by(self, step, ie):

        end_stop = False

        if step != 0:
            self.needs_drawing()
        if self._num_options == -1:
            end_stop = not self.scroll_area.scroll_by(step)
        else:
            self._selection = self._selection + step
            if self._selection < 0:
                self._selection = 0
                end_stop = True
            elif self._selection > self._num_options - 1:
                self._selection = self._num_options - 1
                end_stop = True

        if not end_stop:
            ie.absorb()
        return ie

    def key_input(self, input_event):
        input_event = super(FQBN_Board_Details, self).key_input(input_event)
        key = input_event.key
        if key is None or self._focus == False:
            return input_event
        step = 0
        if key == 258:  # Down Arrow
            return self.step_by(1, input_event)
        elif key == 336:  # Shift-Down Arrow
            return self.step_by(5, input_event)
        elif key == 259:  # Up Arrow
            return self.step_by(-1, input_event)
        elif key == 337:  # Shift-Up Arrow
            return self.step_by(-5, input_event)
        else:
            return input_event  # Unknown key - pass it back to the driver
        input_event.absorb()
        return input_event

    def process(self, time):
        sel = self._board_list_obj.get_selection()
        if sel != self._selected_index or (self.data_loader.has_new_data() and self.current_selection_unloaded):
            self._selected_index = sel
            self.needs_drawing()
            self.data = self.data_loader.get_current_data()

            self._lines = []

            fqbn = self.devices[self._selected_index]['FQBN']
            if fqbn in self.data:
                details = self.data[fqbn]
                required_tools = details['required_tools']
                options = details['config_options'] if 'config_options' in details else []
                self._lines.append(Text_Line(details['name'], curses.color_pair(7)|curses.A_UNDERLINE))
                self._lines.append(Text_Line('', curses.color_pair(1)))

                if required_tools:
                    self._lines.append(Text_Line('Required Tools: ', curses.color_pair(1), required_tools[0]['name'] + ' ', curses.color_pair(5), required_tools[0]['version'], curses.color_pair(7)))
                    first = True
                    for tool in required_tools:
                        if first:
                            first = False
                            continue
                        self._lines.append(Text_Line('                ' + tool['name'] + ' ', curses.color_pair(5), tool['version'], curses.color_pair(7)))
                # {
                #     "option": "debug",
                #     "option_label": "Debug",
                #     "values": [
                #         {
                #         "value": "off",
                #         "value_label": "Off",
                #         "selected": true
                #         },
                #         {
                #         "value": "on",
                #         "value_label": "On"
                #         }
                #     ]
                # }

                if options:
                    # longest_label = 0
                    # for opt in options:
                    #     for vals in opt['values']:
                    #         if len(vals['value_label']) > longest_label:
                    #             longest_label = len(vals['value_label']) + 2

                    for opt in options:
                        label = opt['option_label']
                        opt_val = opt['option']
                        self._lines.append(Text_Line(label + ' ', curses.color_pair(5), opt_val, curses.color_pair(2)))
                        for vals in opt['values']:
                            option_text = opt_val + '=' + vals['value']
                            spreader = '┄' * (self._w - len(vals['value_label']) - len(option_text) - self.border_width_reduction - 4)
                            if 'cursor' in vals and vals['cursor'] is True:
                                self._lines.append(Text_Line('   ' + vals['value_label'], curses.color_pair(7), spreader, curses.color_pair(11), option_text, curses.color_pair(9)))
                            else:
                                self._lines.append(Text_Line('   ' + vals['value_label'], curses.color_pair(7), spreader, curses.color_pair(11), option_text, curses.color_pair(2)))
                            
                self.current_selection_unloaded = False
            else:
                self._lines.append(Text_Line('Board not loaded.', curses.color_pair(3)))

            self.scroll_area.update_lines(self._lines)

        # self.local_notifications.process(time)
        

    def focus(self):
        super(FQBN_Board_Details, self).focus()


    def draw(self):
        if not self.get_needs_drawing():
            return
        self.init_frame(title=self.title)

        if self._selected_index != -1:
            # The user has selected a board
            self.scroll_area.calculate_trimmed_lines()
            scroll = self.scroll_area.get_scroll_bar()
            display_lines = self.scroll_area.get_trimmed_lines()
            screen_index = 0
            for l in display_lines:
                l.output_to_window(self._win, self.line_counter, 2)
                if scroll is not None:
                    if not scroll[screen_index]:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(2), inc=False)
                    else:
                        self.addstr_auto(self._w-4, '▊', color=curses.color_pair(1), inc=False)
                self.inc()
                screen_index = screen_index + 1

        # self.local_notifications.draw(force=True)
        super(FQBN_Board_Details, self).draw()

class Data_Loader(Processable, Init):
    def __init__(self, devices, notification_pane=None, save_data=True):
        self.devices = devices
        self.save_data = {}
        self.results = None
        self.transient_results = None
        self.worker_list = []
        self.loading_data = False
        self.notification_pane = notification_pane
        self.old_data = {}
        self.log_index = 0
        self.new_data_flag = False
        self.data_load_started = False
        self._save_data = save_data

        self.num_to_load = 0
        self.num_loaded = 0

    def thread_arduino_cli_board_details(self, fqbn, results, transient_results):
        details_raw = subprocess.run(
            f'arduino-cli board details {fqbn} --format json', shell=True, capture_output=True)
        results[fqbn] = json.loads(details_raw.stdout)
        transient_results.append(fqbn)

    def check_on_workers(self):
        if not self.loading_data:
            return
        remove_list = []
        still_alive = False
        for w in self.worker_list:
            if not w.is_alive():
                remove_list.append(w)
                self.num_loaded = self.num_loaded + 1
            else:
                still_alive = True

        for _remove in remove_list:
            self.worker_list.remove(_remove)

        if remove_list:
            self.new_data_flag = True
            self.loading_bar.set(self.num_loaded / self.num_to_load, new_message=remove_list[0].name)
            self.notification_pane.notify(self.loading_bar.get_text(), notification_duration=-1, loading_square=True)

        if not still_alive:
            self.loading_data = False
            # self.notification_callback('Loading device data...Done!', notification_duration=2)
            self.loading_bar.set(1, new_message=f'Done! {len(self.devices)} devices loaded.')
            self.notification_pane.notify(self.loading_bar.get_text(), notification_duration=4, loading_square=True, loading_square_done=True)
            
            for key, value in self.results.items():
                self.save_data[key] = value
            if self._save_data:
                with open(self.save_file, 'w') as outfile:
                    json.dump(self.save_data, outfile)

    def get_data(self):
        if self.loading_data is False:
            return self.save_data
        return None

    def has_all_data(self):
        return not self.loading_data and len(self.save_data) != 0

    def has_new_data(self):
        return self.new_data_flag

    def get_new_data(self, clear=True):
        output = {}
        current_data = self.results.copy()
        for key, value in current_data.items():
            if key not in self.old_data:
                output[key] = value
        if clear:
            self.old_data = current_data
        return output

    def get_current_data(self):
        return self.save_data.copy()

    def init(self, file_name='device_data.json', force_reload=False):
        self.loading_bar = Loading_Bar(f'Loading {len(self.devices)} devices...', self.notification_pane.get_max_message_length(using_loading_square=True), allocate_message_width=30)
        if self.data_load_started and force_reload is False:
            return
        self.data_load_started = True
        self.save_file = file_name
        # TODO: Make starting workers faster (or non-blocking)
        try:
            with open(self.save_file) as f:
                self.save_data = json.load(f)
        except IOError:
            pass
        except json.decoder.JSONDecodeError:
            self.save_data = {}

        self.results = {}
        self.transient_results = []

        for d in self.devices:
            if d['FQBN'] not in self.save_data:
                x = threading.Thread(target=self.thread_arduino_cli_board_details, args=(d['FQBN'], self.results, self.transient_results))
                x.daemon = True
                x.name=d['FQBN']
                x.start()
                self.worker_list.append(x)

        self.num_to_load = len(self.worker_list)
        self.num_loaded = len(self.devices) - self.num_to_load

        if len(self.worker_list) != 0:
            # self.notification_callback('Loading device data...', notification_duration=-1, loading_square=True)
            self.loading_bar.set(0)
            self.notification_pane.notify(self.loading_bar.get_text(), notification_duration=-1, loading_square=True)
            self.loading_data = True

    def process(self, time):
        self.check_on_workers()

class FQBN_Board_List(Pane):

    def __init__(self, stdscr, devices, data_loader, notification_pane=None):
        super(FQBN_Board_List, self).__init__(stdscr)
        self._devices = devices
        self._selection = 0
        self.title = f'Board List ({len(devices)} devices)'
        self._num_options = len(devices)
        self._selection_change_callback = None
        self.notification_pane = notification_pane
        self.data_loader = data_loader
        self.loaded_boards = []
        self.loaded_data = False

        self.color_loaded = curses.color_pair(9)  # Green
        self.color_unloaded = curses.color_pair(2)  # Dim Default

        self.selected_true = '>'
        self.selected_false = ' '

        self.num_pad_len = len(str(len(devices)))
        self.num_pad_len_width = self.num_pad_len + 2

        if len(self.selected_true) != len(self.selected_false):
            raise ValueError(f'Selection markers must be the same length: \'selected_true\':len={len(self.selected_true)} vs. \'selected_false\':len={len(self.selected_false)}')

    def __str__(self):
        return 'L'

    def assign_win(self, win):
        super(FQBN_Board_List, self).assign_win(win)

        if len(self.title) + self.border_width_reduction > self._w:
            raise TerminalTooSmallError

        self.selection_width_reduction = len(self.selected_true)

        self.lines = []
        for d in self._devices:
            # lines.append(d['name'])
            self.lines.append(Text_Line(d['name'], self.color_unloaded, data={'cursor':False, 'loaded':False, 'fqbn':d['FQBN']}))

        self.scroll_area = Scroll_Area(self._h - self.border_height_reduction,
            self._w - self.border_width_reduction - self.selection_width_reduction - self.num_pad_len_width, \
            self._selection, lines=self.lines)

    def focus(self):
        super(FQBN_Board_List, self).focus()

    def get_line_by_fqbn(self, fqbn):
        for l in self.lines:
            if l.data['fqbn'] == fqbn:
                return l
        return None

    def step_by(self, step, ie):
        if step != 0:
            self.needs_drawing()
        sel = self._selection + step
        end_stop = False
        if sel < 0:
            sel = 0
            end_stop = True
        elif sel > self._num_options - 1:
            sel = self._num_options - 1
            end_stop = True
        self.selection(sel)

        if not end_stop:
            ie.absorb()
        return ie

    def key_input(self, input_event):
        input_event = super(FQBN_Board_List, self).key_input(input_event)
        key = input_event.key
        if key is None or self._focus == False:
            return input_event
        step = 0
        if key == 258:  # Down Arrow
            return self.step_by(1, input_event)
        elif key == 336:  # Shift-Down Arrow
            return self.step_by(5, input_event)
        elif key == 259:  # Up Arrow
            return self.step_by(-1, input_event)
        elif key == 337:  # Shift-Up Arrow
            return self.step_by(-5, input_event)
        elif key == curses.KEY_MOUSE:
            try:
                _, self._mx, self._my, _, _ = input_event.get_mouse()
                offset_y, _ = self._win.getbegyx()
                self.selection(self._my - offset_y - math.ceil(self.border_height_reduction / 2) + self.scroll_area.mouse_y_offset)
            except curses.error:
                pass
            input_event.absorb()
        else:
            return input_event  # Unknown key - pass it back to the driver
        
        input_event.absorb()
        
        return input_event

    def board_loaded(self, index):
        if not self.loaded_boards:
            return
        # print("B", self.loaded_boards[0])
        return self._devices[index]['FQBN'] in self.loaded_boards

    def process(self, time):
        if self.loaded_data:
            return
        if self.data_loader.has_all_data():
            self.needs_drawing()
            for l in self.lines:
                loaded = l.data['loaded']
                if not loaded:
                    l.data['loaded'] = True
                    l.uniform_color(self.color_loaded)
        elif self.data_loader.has_new_data():
            self.needs_drawing()
            d = self.data_loader.get_new_data()
            for key, _ in d.items():
                l = self.get_line_by_fqbn(key)
                l.data['loaded'] = True
                l.uniform_color(self.color_loaded)

    def selection(self, selection):
        self._selection = selection
        self.scroll_area.cursor(self._selection)
        if self._selection_change_callback is not None:
            self._selection_change_callback(self._selection)

    def get_selection(self):
        return self._selection

    def set_selection_change_callback(self, func):
        self._selection_change_callback = func

    def draw(self):
        if not self.get_needs_drawing():
            return
        self.init_frame(title=self.title)
        
        self.scroll_area.calculate_trimmed_lines()
        lines = self.scroll_area.get_trimmed_lines()
        index = self.scroll_area.get_first_index()
        scroll = self.scroll_area.get_scroll_bar()
        screen_index = 0
        for l in lines:

            s = l.data['cursor']
            self.addstr_auto(0, self.selected_true if s else self.selected_false, inc=False)

            self.addstr_auto(len(self.selected_true), (str(index)+':').ljust(self.num_pad_len_width, ' '), curses.color_pair(1), inc=False)

            l.output_to_window(self._win, self.line_counter, len(self.selected_true)+self.num_pad_len_width+2)
            # self.addstr_auto(len(self.selected_true)+self.num_pad_len_width, str(l), inc=False)
            if scroll is not None:
                if not scroll[screen_index]:
                    self.addstr_auto(self._w-4, '▊', color=curses.color_pair(2), inc=False)
                else:
                    self.addstr_auto(self._w-4, '▊', color=curses.color_pair(1), inc=False)
            self.inc()
            index = index + 1
            screen_index = screen_index + 1

        super(FQBN_Board_List, self).draw()

class Board_Picker_Menu(Scroll_Pane):
    def __init__(self, stdscr, fqbn, notification_box):
        super(Board_Picker_Menu, self).__init__(stdscr, Scroll_Pane_Type.MULTI_SELECT)

        self._notification_box = notification_box

        l = []
        for d in range(0, 50):
            t = Text_Line(f'This is a test!', curses.color_pair(7), f' {d}', curses.color_pair(2))
            l.append(t)

        self.set_contents(l)

class Loading_Bar(object):
    def __init__(self, base_message, width, allocate_message_width=None):
        if not isinstance(base_message, Text_Line):
            base_message = Text_Line(base_message, curses.color_pair(1))
        self._base_message = base_message
        if allocate_message_width is None:
            self._base_message_length = len(self._base_message)
        else:
            self._base_message_length = allocate_message_width
            self._base_message.shorten_to_length(self._base_message_length)
        self._message = self._base_message
        self._w = width
        self._fraction_done = 0
    
    def set(self, fraction_done, new_message=None):
        self._fraction_done = fraction_done
        if self._fraction_done > 1:
            self._fraction_done = 1
        elif self._fraction_done < 0:
            self._fraction_done = 0

        if new_message is not None:
            if not isinstance(new_message, Text_Line):
                new_message = Text_Line(new_message, curses.color_pair(1))
            self._message = new_message
            self._message.shorten_to_length(self._base_message_length)

    def get_text(self):
        bar_len = self._w - self._base_message_length - 8
        if bar_len < 2:
            return Text_Line(
                self._message, curses.color_pair(1),
                ('{:.0%}'.format(self._fraction_done)).ljust(4, ' '), curses.color_pair(1)
            )
        else:
            msg = self._message
            num_filled = math.floor(bar_len * self._fraction_done)
            num_not_filled = bar_len - num_filled
            # bar = '[' + ('━' * num_filled) + (' ' * num_not_filled) + ']'
            # return ('{:.0%}'.format(self._fraction_done)).rjust(4, ' ') + bar + ' ' + msg
            if self._fraction_done == 1:
                precent_color = curses.color_pair(9)
            else:
                precent_color = curses.color_pair(5)
            return Text_Line(
                ('{:.0%}'.format(self._fraction_done)).rjust(4, ' '), precent_color,
                '[', curses.color_pair(1),
                ('━' * num_filled), curses.color_pair(1),
                ('━' * num_not_filled), curses.color_pair(2),
                '] ', curses.color_pair(1),
                msg, curses.color_pair(1)
            )

class Notification_Box(Pane):
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
          
            if isinstance(text, Text_Line):
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

class Menu_Item(object):
    def __init__(self, text, callback, hotkey=None, underline_char=-1, disabled=False):
        self.text = text
        self.callback = callback
        self._x = 0
        self._y = 0
        self._selected = False
        self._hotkey = hotkey
        self._hotkey_ord = ord(hotkey) if hotkey is not None else None
        self._underline_char = underline_char
        self._disabled = disabled

        if underline_char != -1:
            self._underline_char_before = self.text[0:self._underline_char]
            self._underline_char_underline = self.text[self._underline_char:self._underline_char+1]
            self._underline_char_after = self.text[self._underline_char+1:]
            if self._hotkey is not None:
                self._underline_char_after = self._underline_char_after + f' ({self._hotkey})'

        if self._hotkey is not None:
            self.text = self.text + f' ({self._hotkey})'

    def set_center(self, x, y):
        self._x = x
        self._y = y

    def set_disabled(self, val):
        self._disabled = val

    def get_disabled(self):
        return self._disabled

    def key_input(self, input_event):
        if self._hotkey_ord is not None and input_event.key == self._hotkey_ord:
            if self.click():
                input_event.absorb()

        return input_event

    def click(self):
        if self.callback is not None and not self._disabled:
            self.callback()
            return True
        return False

    def select(self, val=True):
        self._selected = val

    def get_center(self):
        return (self._x, self._y)

    def get_left_corner(self):
        return (self._x - math.ceil(len(self.text)), self._y)

    def draw(self, win):
        (x, y) = self.get_left_corner()
        color = curses.color_pair(1) # Default
        if self._disabled:
            color = curses.color_pair(2) # Dim default
        if self._selected:
            win.addstr(y, x, self.text, color | curses.A_UNDERLINE)
        else:
            if self._underline_char != -1:
                win.addstr(y, x, self._underline_char_before, color)
                win.addstr(y, x + len(self._underline_char_before), self._underline_char_underline, color | curses.A_UNDERLINE)
                win.addstr(y, x + len(self._underline_char_before) + len(self._underline_char_underline), self._underline_char_after, color)
            else:
                win.addstr(y, x, self.text, color)

class Menu_Pane(Pane):
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
        elif key == 260: # Left Arrow
            return self.move_menu_cursor(-1, input_event)
        elif key == 10 or key == 32: # Enter key or space key
            return self.click_menu_item(input_event)
        else:
            input_event = self.check_menu_hotkeys(input_event)
            return input_event  # Unknown key - pass it back to the driver

        input_event.absorb()

        return input_event

    def calculate_menu_locations(self):
        divisor =  math.ceil(self._w / (len(self._menu_items) + 1))
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
