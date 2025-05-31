# import unittest
# import json
# import azure.functions as func
# import os
# import sys

# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
# if PROJECT_ROOT not in sys.path:
#     sys.path.insert(0, PROJECT_ROOT)

# # Import the function handlers and shared components
# # This import will trigger model loading from shared_code.app_setup
# try:
#     from function_app import predict_sentiment, root_endpoint, model, tokenizer, logger
# except ImportError as e:
#     print(f"Failed to import function_app or shared_code modules: {e}")
#     print(f"PROJECT_ROOT: {PROJECT_ROOT}")
#     print(f"sys.path: {sys.path}")
#     # This is a common point of failure if the paths aren't set up correctly for unittest
#     raise

# class TestAzureFunctions(unittest.TestCase):

#     @classmethod
#     def setUpClass(cls):
#         """
#         This method is called once before any tests in the class are run.
#         We can use it to check if the model loaded correctly.
#         """
#         logger.info("Unittest setUpClass: Checking model and tokenizer.")
#         if model is None or tokenizer is None:
#             raise unittest.SkipTest("Model or tokenizer failed to load. Skipping tests.")
#         logger.info("Model and tokenizer are loaded for unittests.")

#     def _create_mock_http_request(
#         self,
#         method: str,
#         url: str,
#         body: dict = None,
#         params: dict = None,
#         headers: dict = None,
#         route_params: dict = None
#     ) -> func.HttpRequest:
#         """Helper function to create a mock HttpRequest."""
#         req_body_bytes = json.dumps(body).encode('utf-8') if body else None
#         req_headers = headers if headers else {}
#         if body and 'content-type' not in (key.lower() for key in req_headers.keys()):
#             req_headers['Content-Type'] = 'application/json'

#         return func.HttpRequest(
#             method=method,
#             url=url,
#             headers=req_headers,
#             params=params,
#             route_params=route_params,
#             body=req_body_bytes
#         )

#     def test_root_endpoint(self):
#         """Test the root ('/') endpoint."""
#         req = self._create_mock_http_request(method="GET", url="http://localhost/api/")

#         # Call the function handler directly
#         # For v2 model, access the user function via .build().get_user_function()
#         response_obj = root_endpoint.build().get_user_function()(req)

#         self.assertEqual(response_obj.status_code, 200)
#         response_body = json.loads(response_obj.get_body().decode())
#         expected_response = {"message": "API de prédiction de sentiment pour Air Paradis"}
#         self.assertEqual(response_body, expected_response)

#     def test_predict_positive_sentiment(self):
#         """Test the /predict endpoint with positive sentiment."""
#         payload = {"text": "I love this company! The service was excellent!!!"}
#         req = self._create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

#         response_obj = predict_sentiment.build().get_user_function()(req)

#         self.assertEqual(response_obj.status_code, 200)
#         response_data = json.loads(response_obj.get_body().decode())

#         self.assertIn("sentiment", response_data)
#         self.assertEqual(response_data["sentiment"], "positif")
#         self.assertIn("probability", response_data)
#         self.assertIsInstance(response_data["probability"], float)

#     def test_predict_negative_sentiment(self):
#         """Test the /predict endpoint with negative sentiment."""
#         payload = {"text": "What a bad flight. It was late and the service was bad :("}
#         req = self._create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

#         response_obj = predict_sentiment.build().get_user_function()(req)

#         self.assertEqual(response_obj.status_code, 200)
#         response_data = json.loads(response_obj.get_body().decode())

#         self.assertIn("sentiment", response_data)
#         self.assertEqual(response_data["sentiment"], "negatif")
#         self.assertIn("probability", response_data)
#         self.assertIsInstance(response_data["probability"], float)

#     def test_predict_invalid_input_missing_text(self):
#         """Test /predict with invalid input (missing 'text' field)."""
#         payload = {"message": "This is not the expected input structure"}
#         req = self._create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

#         response_obj = predict_sentiment.build().get_user_function()(req)
#         self.assertEqual(response_obj.status_code, 400)
#         response_data = json.loads(response_obj.get_body().decode())
#         self.assertIn("error", response_data)
#         self.assertEqual(response_data["error"], "Invalid request body")
        
# if __name__ == '__main__':
#     unittest.main()