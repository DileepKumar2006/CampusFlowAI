"""Regression tests for fixes made after the browser-based review."""
import unittest
from campusflow.nlp import extract


class SpacedRoomReferences(unittest.TestCase):
    def test_spaced_room_is_recognised(self):
        self.assertEqual(extract("The projector in B 204 is broken, 40 students at 3 PM")["room"], "B204")

    def test_people_and_time_numbers_are_not_rooms(self):
        self.assertIsNone(extract("A 100 students need a room")["room"])
        self.assertIsNone(extract("Meet at C 101 pm")["room"])

    def test_lowercase_spaced_is_not_a_room(self):
        self.assertIsNone(extract("we need a 100 seat hall")["room"])

    def test_earliest_mention_wins(self):
        self.assertEqual(extract("B 204 and A101 both fail")["room"], "B204")
        self.assertEqual(extract("A101 and B 204 both fail")["room"], "A101")

    def test_existing_formats_unchanged(self):
        for t in ("room b204 has no AC", "projector in B-204 broken", "B204 projector"):
            self.assertEqual(extract(t)["room"], "B204", t)


if __name__ == "__main__":
    unittest.main()
