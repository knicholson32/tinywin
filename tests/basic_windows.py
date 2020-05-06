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
            t = core.Text_Line(f'This is a test!', curses.color_pair(7), f' {d}', curses.color_pair(2))
            l.append(t)

        self.set_contents(l)


class Test_Pane2(panes.Scroll_Pane):
    def __init__(self, stdscr, notification_box, test_pane):
        super(Test_Pane2, self).__init__(stdscr, panes.Scroll_Pane_Type.SINGLE_SELECT)

        self._notification_box = notification_box

        self._test_pane = test_pane

        l = []
        for d in range(0, 50):
            t = core.Text_Line('Text line 1 ', curses.color_pair(5)) + "test 2"
            # t = "test"
            l.append(t)

        self.set_contents(l)

        self._test_pane.attach_selection_changed_callback(self.selection_change)

        self.set_header_line(core.Text_Line('This is my header!!123123123123123123123123123123123123123123123123qweqweqweqweqwqweqwqweqweqweqw', curses.color_pair(5)))

    def selection_change(self, selection_arr):
        if len(selection_arr) > 0:
            self.cursor(selection_arr[0])
            self.needs_drawing()


def main_test(stdscr):
    main_scr = screen.Screen(stdscr)

    notification_box = panes.Notification_Box(stdscr)
    test_pane = Test_Pane(stdscr, notification_box)
    test_pane2 = Test_Pane2(stdscr, notification_box, test_pane)

    screen_builder = screen.Screen_Builder(stdscr,            2,     1, title='Avaliable Targets')
    #                                       start_x, start_y, width, height, one_line=False
    screen_builder.add_pane(test_pane,      0,       0,       1,     1)
    screen_builder.add_pane(test_pane2,     1,       0,       1,     1)

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

