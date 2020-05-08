import os
import sys
import curses
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinywin import screen, panes, core, helpers


class Test_Pane(panes.Scroll_Pane):
    def __init__(self, stdscr, notification_box):
        super(Test_Pane, self).__init__(stdscr, panes.Scroll_Pane_Type.MULTI_SELECT)

        self._notification_box = notification_box

        l = []
        for d in range(0, 50):
            t = core.Text_Line('This is a test!', curses.color_pair(7), f' {d}', curses.color_pair(2))
            l.append(t)

        self.set_contents(l)

    # def draw(self):
        # super(Test_Pane, self).draw()


class Test_Pane2(panes.Scroll_Pane):
    def __init__(self, stdscr, notification_box, test_pane):
        super(Test_Pane2, self).__init__(stdscr, panes.Scroll_Pane_Type.SINGLE_SELECT, title='Test2')

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
        self.set_footer_line(core.Text_Line('This is my footer!!123123123123123123123123123123123123123123123123qweqweqweqweqwqweqwqweqweqweqw', curses.color_pair(5)))


    def selection_change(self, selection_arr):
        if len(selection_arr) > 0:
            self.cursor(selection_arr[0])
            self.needs_drawing()

    def draw(self):
        if self._needs_drawing is False:
            return
        super(Test_Pane2, self).draw()

        self.addstr(2, 2, core.Text_Line('This is my string!', curses.color_pair(7)))
        self._win.refresh()


class Test_Screen_Pane(panes.Screen_Pane):
    def __init__(self, stdscr):
        super(Test_Screen_Pane, self).__init__(stdscr, title='Screen Pane')



    def assign_win(self, win):
        

        self._h, self._w = win.getmaxyx()

        self.sub_win = win.derwin(self._h - 2, self._w - 2, 1, 1)
        # self.sub_win.mvwin(20, 20)

        notification_box = panes.Notification_Box(self.sub_win)
        test_pane = Test_Pane(self.sub_win, notification_box)
        test_pane2 = Test_Pane(self.sub_win, notification_box)

        screen_builder = screen.Screen_Builder(self.sub_win,            1,     2, frameless=True)
        screen_builder.add_pane(test_pane,     0,       0,       1,     1)
        screen_builder.add_pane(test_pane2,     0,       1,       1,     1)

        # screen_builder.add_footer(notification_box)

        self.assign_screen_builder(screen_builder)


        super(Test_Screen_Pane, self).assign_win(win)




        



def main_test(stdscr):
    main_scr = screen.Screen(stdscr)

    notification_box = panes.Notification_Box(stdscr)
    test_pane = Test_Pane(stdscr, notification_box)
    test_pane2 = Test_Pane2(stdscr, notification_box, test_pane)

    test_screen_pane = Test_Screen_Pane(stdscr)
    

    screen_builder = screen.Screen_Builder(stdscr,            2,     1, title='Avaliable Targets')
    #                                       start_x, start_y, width, height, one_line=False
    screen_builder.add_pane(test_screen_pane,      0,       0,       1,     1)
    screen_builder.add_pane(test_pane2,     1,       0,       1,     1)
    # screen_builder.add_pane(test_pane2,     1,       0,       1,     1)

    screen_builder.add_footer(notification_box)
    main_scr.build(screen_builder)
    main_scr.init()
    interacting = True
    while interacting:
        interacting = main_scr.frame()

    print('done')


if __name__ == '__main__':
    stdscr = helpers.curses_init()
    curses.wrapper(main_test)
    helpers.curses_destroy(stdscr)

