import unittest

import main


class MainAppStructureTests(unittest.TestCase):
    def test_root_route_is_registered_once(self):
        root_get_routes = [
            route for route in main.app.routes
            if getattr(route, "path", None) == "/" and "GET" in (getattr(route, "methods", set()) or set())
        ]
        self.assertEqual(len(root_get_routes), 1)

    def test_api_status_route_is_separate(self):
        paths = {getattr(route, "path", None) for route in main.app.routes}
        self.assertIn("/api", paths)
        self.assertIn("/health", paths)


if __name__ == "__main__":
    unittest.main()
