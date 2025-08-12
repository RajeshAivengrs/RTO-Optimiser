import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { Input } from './ui/input';

// Icons from lucide-react
import { 
  TrendingUp, 
  TrendingDown, 
  Package, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  MessageSquare,
  MapPin,
  Phone,
  RefreshCw,
  DollarSign,
  Shield,
  FileText
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const SellerDashboard = ({ brandId = 'demo-brand-001' }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderDetails, setOrderDetails] = useState(null);
  const [challengeDialog, setChallengeDialog] = useState(false);
  const [challengeData, setChallengeData] = useState({
    reason: '',
    comments: '',
    evidenceRequired: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    fetchAlerts();
    
    // Refresh data every 2 minutes
    const interval = setInterval(() => {
      fetchDashboardData();
      fetchAlerts();
    }, 120000);
    
    return () => clearInterval(interval);
  }, [brandId]);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/seller/dashboard/${brandId}?period=week`);
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
        setLoading(false);
      } else {
        // Fallback to mock data for demo
        setDashboardData({
          brand_id: brandId,
          period: 'week',
          total_orders: 245,
          successful_deliveries: 198,
          success_rate: 80.8,
          verified_ndrs: 12,
          suspicious_ndrs: 8,
          rto_prevented: 15,
          cost_saved: 3000,
          carrier_breakdown: [
            {
              carrier: 'Delhivery',
              total_orders: 150,
              success_rate: 85.3,
              verified_ndrs: 8,
              suspicious_ndrs: 3,
              rto_prevented: 10
            },
            {
              carrier: 'Shiprocket',
              total_orders: 95,
              success_rate: 74.7,
              verified_ndrs: 4,
              suspicious_ndrs: 5,
              rto_prevented: 5
            }
          ]
        });
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to fetch dashboard data');
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/seller/alerts/${brandId}`);
      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
      } else {
        // Mock alerts for demo
        setAlerts([
          {
            type: 'SUSPICIOUS_NDR_PATTERN',
            severity: 'medium',
            title: 'Suspicious NDR Activity',
            message: '8 suspicious NDRs detected this week in Bengaluru area',
            action_required: true,
            suggestions: ['Review NDR events', 'Challenge invalid attempts', 'Escalate to carrier']
          },
          {
            type: 'COST_SAVINGS',
            severity: 'info',
            title: 'RTO Prevention Success',
            message: '₹3,000 saved by preventing 15 RTOs this week',
            action_required: false,
            suggestions: []
          }
        ]);
      }
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  };

  const fetchOrderDetails = async (orderId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/seller/orders/${brandId}/${orderId}`);
      if (response.ok) {
        const data = await response.json();
        setOrderDetails(data);
      } else {
        // Mock order details for demo
        setOrderDetails({
          order_id: orderId,
          status: 'NDR_RECEIVED',
          delivery_attempts: [
            {
              timestamp: new Date().toISOString(),
              event_code: 'NDR',
              location: 'Bengaluru Hub',
              description: 'Customer unavailable for delivery'
            }
          ],
          ndr_details: {
            ndr_code: 'CUSTOMER_UNAVAILABLE',
            ndr_reason: 'No response from customer',
            proof_required: true,
            proof_validated: false
          },
          proof_validation: {
            gps_coordinates: {
              provided: [12.9716, 77.5946],
              required: [12.9716, 77.5946]
            },
            gps_distance_meters: 450,
            gps_valid: false,
            call_log: {
              duration_sec: 8,
              outcome: 'NO_RESPONSE',
              valid: false
            },
            violations: [
              'GPS location 450m from delivery address (max: 200m)',
              'Call duration 8s (min: 10s)'
            ]
          },
          carrier_performance: {
            carrier: 'Shiprocket',
            recent_performance: {
              total_shipments: 95,
              delivery_rate: 74.7,
              avg_delivery_time: '2.3 days'
            }
          },
          cost_impact: {
            order_value: 1299,
            delivery_cost: 50,
            potential_rto_cost: 200,
            total_risk: 1499
          }
        });
      }
    } catch (err) {
      console.error('Failed to fetch order details:', err);
    }
  };

  const handleChallengeNDR = async () => {
    if (!selectedOrder || !challengeData.reason) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/seller/challenge-ndr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: selectedOrder,
          challenge_reason: challengeData.reason,
          evidence_required: challengeData.evidenceRequired,
          seller_comments: challengeData.comments
        })
      });
      
      if (response.ok) {
        setChallengeDialog(false);
        setChallengeData({ reason: '', comments: '', evidenceRequired: [] });
        // Refresh data
        fetchDashboardData();
        fetchOrderDetails(selectedOrder);
      }
    } catch (err) {
      console.error('Failed to challenge NDR:', err);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'info': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-600" />
          <span className="text-lg font-medium">Loading Seller Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Seller Transparency Portal</h1>
                <p className="text-sm text-gray-500">Brand: {brandId} • Delivery Accountability Dashboard</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  fetchDashboardData();
                  fetchAlerts();
                }}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <Alert className="mb-6">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* KPI Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Total Orders</h3>
                <p className="text-3xl font-bold text-blue-600">{dashboardData?.total_orders || 0}</p>
              </div>
              <Package className="h-8 w-8 text-blue-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Success Rate</h3>
                <p className="text-3xl font-bold text-green-600">{dashboardData?.success_rate || 0}%</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Suspicious NDRs</h3>
                <p className="text-3xl font-bold text-red-600">{dashboardData?.suspicious_ndrs || 0}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Cost Saved</h3>
                <p className="text-3xl font-bold text-green-600">₹{dashboardData?.cost_saved || 0}</p>
              </div>
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="transparency" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="transparency">Order Transparency</TabsTrigger>
            <TabsTrigger value="carriers">Carrier Performance</TabsTrigger>
            <TabsTrigger value="alerts">Alerts & Actions</TabsTrigger>
            <TabsTrigger value="challenges">NDR Challenges</TabsTrigger>
          </TabsList>

          <TabsContent value="transparency">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Real-Time Order Transparency
                  </h2>
                  <Badge variant="outline">Live Updates</Badge>
                </div>

                <div className="space-y-4">
                  {/* Mock order list */}
                  <div className="border rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div>
                          <p className="font-medium">Order #ORD12345</p>
                          <p className="text-sm text-gray-500">Customer: +91-98765-XXXXX</p>
                        </div>
                        <Badge variant="destructive">NDR - Suspicious</Badge>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setSelectedOrder('ORD12345');
                            fetchOrderDetails('ORD12345');
                          }}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View Details
                        </Button>
                        <Button 
                          variant="default" 
                          size="sm"
                          onClick={() => {
                            setSelectedOrder('ORD12345');
                            setChallengeDialog(true);
                          }}
                        >
                          Challenge NDR
                        </Button>
                      </div>
                    </div>
                    
                    {selectedOrder === 'ORD12345' && orderDetails && (
                      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                        <h4 className="font-medium mb-3">Delivery Attempt Analysis</h4>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <h5 className="font-medium text-sm text-gray-700 mb-2">GPS Validation</h5>
                            <div className="flex items-center space-x-2">
                              {orderDetails.proof_validation?.gps_valid ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">
                                Distance: {orderDetails.proof_validation?.gps_distance_meters}m 
                                {orderDetails.proof_validation?.gps_valid ? ' (Valid)' : ' (Too far)'}
                              </span>
                            </div>
                          </div>
                          
                          <div>
                            <h5 className="font-medium text-sm text-gray-700 mb-2">Call Validation</h5>
                            <div className="flex items-center space-x-2">
                              {orderDetails.proof_validation?.call_log?.valid ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">
                                Duration: {orderDetails.proof_validation?.call_log?.duration_sec}s
                                {orderDetails.proof_validation?.call_log?.valid ? ' (Valid)' : ' (Too short)'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {orderDetails.proof_validation?.violations?.length > 0 && (
                          <div className="mt-4">
                            <h5 className="font-medium text-sm text-red-700 mb-2">Violations Detected:</h5>
                            <ul className="list-disc list-inside space-y-1">
                              {orderDetails.proof_validation.violations.map((violation, index) => (
                                <li key={index} className="text-sm text-red-600">{violation}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="mt-4 pt-4 border-t">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm text-gray-600">
                                Potential Loss: ₹{orderDetails.cost_impact?.total_risk}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-medium text-orange-600">
                                Action Required: Challenge this NDR
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="carriers">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Carrier Performance Comparison
                </h2>
                
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Carrier</TableHead>
                        <TableHead>Total Orders</TableHead>
                        <TableHead>Success Rate</TableHead>
                        <TableHead>Verified NDRs</TableHead>
                        <TableHead>Suspicious NDRs</TableHead>
                        <TableHead>RTOs Prevented</TableHead>
                        <TableHead>Performance</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dashboardData?.carrier_breakdown?.map((carrier, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{carrier.carrier}</TableCell>
                          <TableCell>{carrier.total_orders}</TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <Progress value={carrier.success_rate} className="w-16" />
                              <span className="text-sm font-medium">{carrier.success_rate}%</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="default" className="bg-green-100 text-green-800">
                              {carrier.verified_ndrs}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="destructive">
                              {carrier.suspicious_ndrs}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="default" className="bg-blue-100 text-blue-800">
                              {carrier.rto_prevented}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {carrier.success_rate > 80 ? (
                              <Badge className="bg-green-100 text-green-800">Excellent</Badge>
                            ) : carrier.success_rate > 70 ? (
                              <Badge variant="secondary">Good</Badge>
                            ) : (
                              <Badge variant="destructive">Needs Improvement</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="alerts">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Active Alerts & Recommendations
                </h2>
                
                <div className="space-y-4">
                  {alerts.map((alert, index) => (
                    <Alert key={index} className={getSeverityColor(alert.severity)}>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-medium mb-1">{alert.title}</h4>
                            <p className="mb-2">{alert.message}</p>
                            {alert.suggestions && alert.suggestions.length > 0 && (
                              <div>
                                <p className="text-sm font-medium mb-1">Recommended Actions:</p>
                                <ul className="list-disc list-inside space-y-1">
                                  {alert.suggestions.map((suggestion, idx) => (
                                    <li key={idx} className="text-sm">{suggestion}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                          {alert.action_required && (
                            <Button size="sm" variant="outline">
                              Take Action
                            </Button>
                          )}
                        </div>
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="challenges">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  NDR Challenge History
                </h2>
                
                <div className="space-y-4">
                  <div className="text-center text-gray-500 py-8">
                    <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <p>No NDR challenges submitted yet.</p>
                    <p className="text-sm">Challenge suspicious delivery attempts to protect your business.</p>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Challenge NDR Dialog */}
        <Dialog open={challengeDialog} onOpenChange={setChallengeDialog}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Challenge NDR - Order #{selectedOrder}</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Challenge Reason</label>
                <select 
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={challengeData.reason}
                  onChange={(e) => setChallengeData({...challengeData, reason: e.target.value})}
                >
                  <option value="">Select reason</option>
                  <option value="GPS_LOCATION_INVALID">GPS location too far from address</option>
                  <option value="INSUFFICIENT_CALL_ATTEMPT">Call duration too short</option>
                  <option value="NO_ACTUAL_ATTEMPT">No genuine delivery attempt made</option>
                  <option value="TIMING_ISSUES">Delivery attempted at wrong time</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium mb-2 block">Additional Comments</label>
                <Textarea 
                  placeholder="Provide additional details about why you're challenging this NDR..."
                  value={challengeData.comments}
                  onChange={(e) => setChallengeData({...challengeData, comments: e.target.value})}
                />
              </div>
              
              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2">
                  <input type="checkbox" className="rounded" />
                  <span className="text-sm">Request GPS proof</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input type="checkbox" className="rounded" />
                  <span className="text-sm">Request call recording</span>
                </label>
              </div>
              
              <div className="flex justify-end space-x-2 pt-4">
                <Button variant="outline" onClick={() => setChallengeDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={handleChallengeNDR} disabled={!challengeData.reason}>
                  Submit Challenge
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
};

export default SellerDashboard;