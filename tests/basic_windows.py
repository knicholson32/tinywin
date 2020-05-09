import os
import sys
import curses
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinywin import screen, panes, core, helpers


class Test_Pane(panes.Scroll_Pane):
    def __init__(self, notification_box):
        super(Test_Pane, self).__init__(panes.Scroll_Pane_Type.MULTI_SELECT, border_style=core.Screen_Border_Style.FULL)

        self._notification_box = notification_box

        l = []
        for d in range(0, 50):
            t = core.Text_Line('This is a test!', curses.color_pair(7), f' {d}', curses.color_pair(2))
            l.append(t)

        self.set_contents(l)

class Test_Pane_Sub(panes.Scroll_Pane):
    def __init__(self, notification_box):
        super(Test_Pane_Sub, self).__init__(panes.Scroll_Pane_Type.MULTI_SELECT, border_style=core.Screen_Border_Style.FULL)

        self._notification_box = notification_box

        l = []
        for d in range(0, 50):
            t = core.Text_Line('This is a test! (sub)', curses.color_pair(7), f' {d}', curses.color_pair(2))
            l.append(t)

        self.set_contents(l)


class Test_Pane2(panes.Scroll_Pane):
    def __init__(self, notification_box, test_pane):
        super(Test_Pane2, self).__init__(panes.Scroll_Pane_Type.SINGLE_SELECT, title='Test2')

        self._notification_box = notification_box

        self._test_pane = test_pane

        l = []
        for d in range(0, 50):
            t = core.Text_Line('Text line 1 ', curses.color_pair(5)) + "test 2"
            # t = "test"
            l.append(t)

        self.set_contents(l)

        self._test_pane.attach_selection_changed_callback(self.selection_change)

        # self.set_header_line(core.Text_Line('This is my header!!123123123123123123123123123123123123123123123123qweqweqweqweqwqweqwqweqweqweqw', curses.color_pair(5)))
        # self.set_footer_line(core.Text_Line('This is my footer!!123123123123123123123123123123123123123123123123qweqweqweqweqwqweqwqweqweqweqw', curses.color_pair(5)))


    def selection_change(self, selection_arr):
        if len(selection_arr) > 0:
            self.cursor(selection_arr[0])
            self.needs_drawing()

    def draw(self):
        if self._needs_drawing is False:
            return
        

        super(Test_Pane2, self).draw()

        self.addstr(2, 2, core.Text_Line('This is my string!', curses.color_pair(7)))
        self.refresh()
        
    

class Test_Screen_Pane(panes.Screen_Pane):
    def __init__(self):
        super(Test_Screen_Pane, self).__init__(title='Screen Pane2')

    def assign_win(self, win):
        
        notification_box = panes.Notification_Box()
        test_pane = Test_Pane(notification_box)
        test_pane2 = Test_Pane(notification_box)

        self.configure_layout(1, 2)
        self.add_pane(test_pane,         0,       0,       1,     1)
        self.add_pane(test_pane2,        0,       1,       1,     1)

        # screen_builder.add_footer(notification_box)


        super(Test_Screen_Pane, self).assign_win(win)


class Main_Screen(panes.Screen_Pane):
    def __init__(self):
        super(Main_Screen, self).__init__(title='Main Screen')

    def assign_win(self, win):
        
        notification_box = panes.Notification_Box()
        test_pane = Test_Pane(notification_box)
        test_pane2 = Test_Pane2(notification_box, test_pane)

        test_screen_pane = Test_Screen_Pane()

        self.configure_layout(2, 1)
        self.add_pane(test_screen_pane,  0,       0,       1,     1)
        self.add_pane(test_pane2,        1,       0,       1,     1)
        self.add_pane(test_pane2,        1,       0,       1,     1)

        # screen_builder.add_footer(notification_box)

        super(Main_Screen, self).assign_win(win)
        

class Sub_Screen(panes.Screen_Pane):
    def __init__(self):
        super(Sub_Screen, self).__init__(
            title='Sub Screen',
            border_style=core.Screen_Border_Style.NO_SIDES)

    def assign_win(self, win):

        notification_box = panes.Notification_Box()
        # test_pane = Test_Pane(notification_box)

        self.configure_layout(1, 1)
        self.add_pane(Test_Pane_Sub(notification_box),  0,       0,       1,     1)

        super(Sub_Screen, self).assign_win(win)

class Main_Screen_simple(panes.Screen_Pane):
    def __init__(self):
        super(Main_Screen_simple, self).__init__(
            title='Main Screen',
            border_style=core.Screen_Border_Style.FULL)

    def assign_win(self, win):

        notification_box = panes.Notification_Box()
        # test_pane = Test_Pane(notification_box)

        self.configure_layout(2, 2)
        self.add_pane(Test_Pane(notification_box),  0,       0,       1,     1)
        self.add_pane(Test_Pane(notification_box),  0,       1,       1,     1)
        self.add_pane(Test_Pane(notification_box),  1,       0,       1,     1)
        self.add_pane(Test_Pane(notification_box),  1,       1,       1,     1)

        super(Main_Screen_simple, self).assign_win(win)



def main_test(stdscr):
    main_screen = Main_Screen()
    main_screen.run_as_top_level(stdscr)


if __name__ == '__main__':
    stdscr = helpers.curses_init()
    curses.wrapper(main_test)
    helpers.curses_destroy(stdscr)

