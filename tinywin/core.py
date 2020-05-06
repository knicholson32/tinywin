import curses

from tinywin import helpers

class PaneError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class Init(object):
    def __init__(self):
        pass

    def init(self):
        pass

class Processable(object):
    def __init__(self):    
        super(Processable, self).__init__()

    def process(self, time):
        pass

    def key_input(self, ie):
        return ie

class Drawable(Processable):
    def __init__(self, win=None):
        super(Drawable, self).__init__()
        self._win = win
        self._calc_win_coords()
        self._needs_drawing = True
        self.win_has_been_assigned = False

    def assign_win(self, win):
        self._win = win
        self._calc_win_coords()
        self.win_has_been_assigned = True

    def _calc_win_coords(self):
        if self._win is not None:
            self._h, self._w = self._win.getmaxyx()
        else:
            self._h = None
            self._w = None

    def process(self, time):
        super(Drawable, self).process(time)

    def draw(self):
        if self._needs_drawing:
            self._refresh()

    def needs_drawing(self):
        self._needs_drawing = True

    def get_needs_drawing(self):
        return self._needs_drawing

    def _refresh(self):
        self._win.refresh()
        self._needs_drawing = False

    def key_input(self, ie):
        return ie

class Pane(Drawable):
    def __init__(self, stdscr, win=None, line_counter=0):
        super(Pane, self).__init__(win=win)
        self._stdscr = stdscr
        self._memory = {}
        self._focus = False
        self.line_counter = line_counter
        self.border_width_reduction = 4
        self.border_height_reduction = 2

    def assign_win(self, win):
        super(Pane, self).assign_win(win)

    def process(self, time):
        super(Pane, self).process(time)

    def draw(self):
        super(Pane, self).draw()

    def add_focus_cursor_data(self, data):
        self.focus_cursor_data = data

    def needs_drawing(self):
        super(Pane, self).needs_drawing()

    def get_needs_drawing(self):
        return super(Pane, self).get_needs_drawing()

    def set_focus(self, focus):
        self._focus = focus
        self.needs_drawing()

    def focus(self):
        self._focus = True
        self.needs_drawing()

    def unfocus(self):
        self._focus = False
        self.needs_drawing()

    def get_focus(self):
        return self._focus

    def _refresh(self):
        super(Pane, self)._refresh()

    def init_frame(self, title='', border_color=None, unfocused_line_color=None, single_line=False, omit_border=False, single_line_x=0, single_line_y=0):
        if not single_line:
            self.omit_border = omit_border
            self.draw_top_border(title, omit_side_borders=omit_border, border_color=border_color, unfocused_line_color=unfocused_line_color)
            if not self.omit_border:
                for i in range(1, self._h-2):
                    self.draw_line_border(focused_line_color=border_color, unfocused_line_color=unfocused_line_color, line=i)
                self.draw_bottom_border(focused_line_color=border_color, unfocused_line_color=unfocused_line_color)
                self.line_counter = 1
        else:
            self.line_counter = 0
            self._win.move(single_line_y, single_line_x)
            self._win.clrtoeol()

    def draw_line_border(self, focused_line_color=None, unfocused_line_color=None, reset_line=True, line=None):
        if focused_line_color is None:
            focused_line_color = curses.color_pair(1)  # Default
        if unfocused_line_color is None:
            unfocused_line_color = focused_line_color
        if line is None:
            line = self.line_counter
        if reset_line:
            self._win.move(line, 0)
            self._win.clrtoeol()
        if self._focus:
            self._win.addstr(line, 0, '│', focused_line_color)  # Default
            self._win.addstr(line, self._w-1, '│', focused_line_color)  # Default
        else:
            self._win.addstr(line, 0, '│', unfocused_line_color)
            self._win.addstr(line, self._w-1, '│', unfocused_line_color)

    def key_input(self, input_event):
        # if not self._focus:
        #     return input_event
        # if input_event.key == curses.KEY_MOUSE:
        #     try:
        #         _, self._mx, self._my, _, _ = input_event.getmouse()
        #         # if self._win.enclose(self._my, self._mx):
        #         #     self.focus()
        #         # else:
        #         #     self.unfocus()
        #     except curses.error as e:
        #         pass
        #     input_event.absorb()
        return input_event

    def draw_top_border(self, _title, focused_title_color=None, omit_side_borders=False, border_color=None, unfocused_line_color=None):
        self._win.move(0, 0)
        self._win.clrtoeol()
        if omit_side_borders:
            helpers.title(self._win, 0, _title, self._focus, unfocused_line_color=unfocused_line_color, focused_line_color=border_color, focused_title_color=focused_title_color, omit_side_borders=True)
        else:
            helpers.title(self._win, 0, _title, self._focus, focused_title_color=focused_title_color, focused_line_color=border_color, unfocused_line_color=unfocused_line_color, omit_side_borders=False)

    def draw_bottom_border(self, focused_line_color=None, unfocused_line_color=None):
        if focused_line_color is None:
            focused_line_color = curses.color_pair(1)  # Default
        if unfocused_line_color is None:
            unfocused_line_color = focused_line_color
        self._win.move(self._h - 2, 0)
        self._win.clrtoeol()
        if self._focus:
            self._win.addstr(self._h - 2, 0, '└' + ''.center(self._w-2, '─') + '┘', focused_line_color)
        else:
            self._win.addstr(self._h - 2, 0, '└' + ''.center(self._w-2, '─') + '┘', unfocused_line_color)

    def addstr_auto(self, x, string, color=None, inc=True):
        if color is None:
            color = curses.color_pair(1)
        self._win.addstr(self.line_counter, x + 2, string, color)  # Move over one place to make space for the border
        if inc:
            self.line_counter = self.line_counter + 1

    def inc(self):
        self.line_counter = self.line_counter + 1

    def reset_line_counter(self):
        self.line_counter = 0

class Pane_Holder(Processable):
    def __init__(self, pane, start_x, start_y, width, height, can_be_focused=True, focus_key=None, one_line=False, fixed_to=None, unfocus_callback=None):
        self._pane = pane
        self._start_x = start_x
        self._start_y = start_y
        self._width = width
        self._height = height
        self._can_be_focused = can_be_focused
        self._focus_key = ord(focus_key) if focus_key is not None else None
        self._one_line = one_line
        self._unfocus_callback = unfocus_callback
        self._fixed_to = fixed_to


    def get_coords(self):
        return (self._start_x, self._start_y, self._width, self._height)

    def get_is_one_line(self):
        return self._one_line

    def get_is_fixed_to(self):
        return self._fixed_to

    def link_win(self, win):
        self._pane.assign_win(win)
        self._win = win

    def get_pane(self):
        return self._pane

    def can_be_focused(self):
        return self._can_be_focused

    def key_input(self, ie):
        if ie is not None and self._focus_key is not None and ie.key == self._focus_key:
            if self._unfocus_callback is not None:
                self._unfocus_callback()
            self._pane.focus()
            ie.absorb()
        return ie

class Text_Wrapper(object):
    def __init__(self, text, color):
        self.text = text
        self.color = color

    def __len__(self):
        return len(self.text)

    def __str__(self):
        return self.text

    def copy(self):
        return Text_Wrapper(self.text, self.color)

class Text_Line(object):
    def __init__(self, *args, data=None, ellipsis_color=None, ellipsis_text='...', allowed_width=None):
        self.data = data
        self._has_been_shortened = False
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
            if t.color is None:
                win.addstr(line_counter, len_counter + x_offset, t.text)
            else:
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

    # TODO: Make the add return a new Text_Line with colors perserved
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

    def get_has_been_shortened(self):
        return self._has_been_shortened

    def shorten_to_length(self, length):
        self._allowed_width = length
        self._has_been_shortened = True
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

class TerminalTooSmallError(PaneError):
    def __init__(self, msg='Terminal too small for application'):
        super(TerminalTooSmallError, self).__init__(msg)

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
        color = curses.color_pair(1)  # Default
        if self._disabled:
            color = curses.color_pair(2)  # Dim default
        if self._selected:
            win.addstr(y, x, self.text, color | curses.A_UNDERLINE)
        else:
            if self._underline_char != -1:
                win.addstr(y, x, self._underline_char_before, color)
                win.addstr(y, x + len(self._underline_char_before), self._underline_char_underline, color | curses.A_UNDERLINE)
                win.addstr(y, x + len(self._underline_char_before) + len(self._underline_char_underline), self._underline_char_after, color)
            else:
                win.addstr(y, x, self.text, color)

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
