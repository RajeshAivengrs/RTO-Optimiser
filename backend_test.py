import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any

class RTOOptimizerTester:
    def __init__(self, base_url="https://ndr-resolver.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict[Any, Any] = None, headers: Dict[str, str] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response_data:
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            self.test_results.append({
                "name": name,
                "success": success,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response": response_data
            })

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )

    def test_order_webhook_valid(self):
        """Test order webhook with valid data"""
        order_data = {
            "order_id": f"test-order-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "brand_id": "test-brand-001",
            "customer_phone": "+919876543210",
            "customer_email": "test@example.com",
            "delivery_address": {
                "line1": "123 Test Street",
                "line2": "Near Test Mall",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
                "country": "India",
                "latitude": 12.9716,
                "longitude": 77.5946
            },
            "items": [
                {
                    "sku": "TEST-SKU-001",
                    "name": "Test Product",
                    "quantity": 2,
                    "unit_price": 999.99,
                    "weight_grams": 500
                }
            ],
            "order_value": 1999.98,
            "payment_mode": "COD",
            "order_date": datetime.now().isoformat(),
            "promised_delivery_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "metadata": {"test": True}
        }
        
        return self.run_test(
            "Order Webhook - Valid Data",
            "POST",
            "api/webhooks/order",
            200,
            order_data
        )

    def test_order_webhook_invalid(self):
        """Test order webhook with invalid data"""
        invalid_data = {
            "order_id": "",  # Invalid empty order_id
            "brand_id": "test-brand"
            # Missing required fields
        }
        
        return self.run_test(
            "Order Webhook - Invalid Data",
            "POST",
            "api/webhooks/order",
            422,  # Validation error
            invalid_data
        )

    def test_courier_event_ndr_valid_proof(self):
        """Test courier event with valid NDR proof (GPS + call duration)"""
        event_data = {
            "shipment_id": f"test-shipment-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "event_code": "NDR",
            "event_description": "Customer unavailable",
            "location": "Bengaluru",
            "timestamp": datetime.now().isoformat(),
            "ndr_code": "CUSTOMER_UNAVAILABLE",
            "ndr_reason": "Customer not available at delivery address",
            "gps_latitude": 12.9716,  # Close to delivery address
            "gps_longitude": 77.5946,
            "call_duration_sec": 15,  # Valid call duration >= 10 seconds
            "call_outcome": "NO_RESPONSE"
        }
        
        return self.run_test(
            "Courier Event - Valid NDR Proof",
            "POST",
            "api/webhooks/courier_event",
            200,
            event_data
        )

    def test_courier_event_ndr_invalid_proof_gps(self):
        """Test courier event with invalid NDR proof (GPS too far)"""
        event_data = {
            "shipment_id": f"test-shipment-gps-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "event_code": "NDR",
            "event_description": "Customer unavailable",
            "location": "Mumbai",  # Far from delivery address
            "timestamp": datetime.now().isoformat(),
            "ndr_code": "CUSTOMER_UNAVAILABLE",
            "ndr_reason": "Customer not available",
            "gps_latitude": 19.0760,  # Mumbai coordinates - too far from Bengaluru
            "gps_longitude": 72.8777,
            "call_duration_sec": 15,  # Valid call duration
            "call_outcome": "NO_RESPONSE"
        }
        
        return self.run_test(
            "Courier Event - Invalid NDR Proof (GPS)",
            "POST",
            "api/webhooks/courier_event",
            200,  # Should still accept but mark as invalid proof
            event_data
        )

    def test_courier_event_ndr_invalid_proof_call(self):
        """Test courier event with invalid NDR proof (call duration too short)"""
        event_data = {
            "shipment_id": f"test-shipment-call-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "event_code": "NDR",
            "event_description": "Customer unavailable",
            "location": "Bengaluru",
            "timestamp": datetime.now().isoformat(),
            "ndr_code": "CUSTOMER_UNAVAILABLE",
            "ndr_reason": "Customer not available",
            "gps_latitude": 12.9716,  # Valid GPS
            "gps_longitude": 77.5946,
            "call_duration_sec": 5,  # Invalid call duration < 10 seconds
            "call_outcome": "NO_RESPONSE"
        }
        
        return self.run_test(
            "Courier Event - Invalid NDR Proof (Call Duration)",
            "POST",
            "api/webhooks/courier_event",
            200,  # Should still accept but mark as invalid proof
            event_data
        )

    def test_courier_event_non_ndr(self):
        """Test courier event that's not NDR (should not require proof)"""
        event_data = {
            "shipment_id": f"test-shipment-delivered-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "event_code": "DELIVERED",
            "event_description": "Package delivered successfully",
            "location": "Bengaluru",
            "timestamp": datetime.now().isoformat()
        }
        
        return self.run_test(
            "Courier Event - Non-NDR Event",
            "POST",
            "api/webhooks/courier_event",
            200,
            event_data
        )

    def test_ndr_resolution_reschedule(self):
        """Test NDR resolution with reschedule action"""
        resolution_data = {
            "order_id": "test-order-reschedule",
            "action": "RESCHEDULE",
            "reschedule_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "customer_response": "Please deliver tomorrow"
        }
        
        return self.run_test(
            "NDR Resolution - Reschedule",
            "POST",
            "api/ndr/resolution",
            200,
            resolution_data
        )

    def test_ndr_resolution_change_address(self):
        """Test NDR resolution with address change"""
        resolution_data = {
            "order_id": "test-order-address",
            "action": "CHANGE_ADDRESS",
            "new_address": {
                "line1": "456 New Street",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560002",
                "country": "India",
                "latitude": 12.9352,
                "longitude": 77.6245
            },
            "customer_response": "Please deliver to new address"
        }
        
        return self.run_test(
            "NDR Resolution - Change Address",
            "POST",
            "api/ndr/resolution",
            200,
            resolution_data
        )

    def test_ndr_resolution_dispute(self):
        """Test NDR resolution with dispute action"""
        resolution_data = {
            "order_id": "test-order-dispute",
            "action": "DISPUTE",
            "customer_response": "I was available, delivery person did not come"
        }
        
        return self.run_test(
            "NDR Resolution - Dispute",
            "POST",
            "api/ndr/resolution",
            200,
            resolution_data
        )

    def test_ndr_resolution_rto(self):
        """Test NDR resolution with RTO action"""
        resolution_data = {
            "order_id": "test-order-rto",
            "action": "RTO",
            "customer_response": "Cancel the order"
        }
        
        return self.run_test(
            "NDR Resolution - RTO",
            "POST",
            "api/ndr/resolution",
            200,
            resolution_data
        )

    def test_ndr_resolution_invalid_order(self):
        """Test NDR resolution with invalid order ID"""
        resolution_data = {
            "order_id": "non-existent-order",
            "action": "RESCHEDULE"
        }
        
        return self.run_test(
            "NDR Resolution - Invalid Order",
            "POST",
            "api/ndr/resolution",
            400,  # Bad request for invalid order
            resolution_data
        )

    def test_analytics_kpis(self):
        """Test analytics KPIs endpoint"""
        return self.run_test(
            "Analytics KPIs",
            "GET",
            "api/analytics/kpis",
            200
        )

    def test_analytics_scorecard(self):
        """Test analytics scorecard endpoint"""
        return self.run_test(
            "Analytics Scorecard",
            "GET",
            "api/analytics/scorecard",
            200
        )

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting RTO Optimizer Backend API Tests")
        print("=" * 60)
        
        # Health check
        self.test_health_check()
        
        # Order webhook tests
        self.test_order_webhook_valid()
        self.test_order_webhook_invalid()
        
        # Courier event tests (NDR proof validation)
        self.test_courier_event_ndr_valid_proof()
        self.test_courier_event_ndr_invalid_proof_gps()
        self.test_courier_event_ndr_invalid_proof_call()
        self.test_courier_event_non_ndr()
        
        # NDR resolution tests
        self.test_ndr_resolution_reschedule()
        self.test_ndr_resolution_change_address()
        self.test_ndr_resolution_dispute()
        self.test_ndr_resolution_rto()
        self.test_ndr_resolution_invalid_order()
        
        # Analytics tests
        self.test_analytics_kpis()
        self.test_analytics_scorecard()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [test for test in self.test_results if not test.get('success', False)]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   - {test['name']}: {test.get('error', 'Status code mismatch')}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = RTOOptimizerTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())