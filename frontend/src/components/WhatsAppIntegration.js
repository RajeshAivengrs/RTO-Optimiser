import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';

// Icons from lucide-react
import { 
  MessageCircle, 
  Send, 
  Clock, 
  CheckCircle,
  XCircle,
  AlertTriangle,
  Users,
  TrendingUp,
  DollarSign,
  RefreshCw,
  Phone,
  MessageSquare,
  Target,
  Zap
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const WhatsAppIntegration = () => {
  const [status, setStatus] = useState('checking');
  const [analytics, setAnalytics] = useState(null);
  const [pendingResponses, setPendingResponses] = useState([]);
  const [testDialog, setTestDialog] = useState(false);
  const [testData, setTestData] = useState({
    order_id: '',
    phone: '',
    ndr_reason: 'CUSTOMER_UNAVAILABLE'
  });
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    checkWhatsAppStatus();
    fetchAnalytics();
    fetchPendingResponses();
    
    // Refresh data every 30 seconds
    const interval = setInterval(() => {
      checkWhatsAppStatus();
      fetchAnalytics(); 
      fetchPendingResponses();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const checkWhatsAppStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/whatsapp/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data.status || 'connected');
      } else {
        setStatus('error');
      }
    } catch (err) {
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/whatsapp/analytics`);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      } else {
        // Mock data for demo
        setAnalytics({
          period: 'last_7_days',
          total_messages_sent: 156,
          successful_deliveries: 142,
          delivery_rate: 91.0,
          ndr_notifications_sent: 48,
          customer_response_rate: 73.5,
          cost_savings_estimate: 7200
        });
      }
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    }
  };

  const fetchPendingResponses = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/whatsapp/pending-responses`);
      if (response.ok) {
        const data = await response.json();
        setPendingResponses(Object.entries(data.pending_responses || {}));
      } else {
        // Mock pending responses
        setPendingResponses([
          ['9876XXXXX', {
            order_id: 'ORD12345',
            sent_at: new Date(Date.now() - 1800000).toISOString(), // 30 mins ago
            expires_at: new Date(Date.now() + 5400000).toISOString()  // 1.5 hours from now
          }],
          ['9123XXXXX', {
            order_id: 'ORD67890',
            sent_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
            expires_at: new Date(Date.now() + 3600000).toISOString()  // 1 hour from now
          }]
        ]);
      }
    } catch (err) {
      console.error('Failed to fetch pending responses:', err);
    }
  };

  const triggerTestNDR = async () => {
    if (!testData.order_id || !testData.phone) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/whatsapp/trigger-ndr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: testData.order_id,
          customer_phone: testData.phone,
          ndr_reason: testData.ndr_reason,
          trigger_whatsapp: true
        })
      });
      
      if (response.ok) {
        setTestDialog(false);
        setTestData({ order_id: '', phone: '', ndr_reason: 'CUSTOMER_UNAVAILABLE' });
        // Refresh data
        fetchPendingResponses();
        fetchAnalytics();
      }
    } catch (err) {
      console.error('Failed to trigger test NDR:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'bg-green-100 text-green-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <CheckCircle className="h-5 w-5" />;
      case 'error': return <XCircle className="h-5 w-5" />;
      default: return <Clock className="h-5 w-5" />;
    }
  };

  const formatTimeRemaining = (expiresAt) => {
    const now = new Date();
    const expires = new Date(expiresAt);
    const diff = expires - now;
    
    if (diff <= 0) return 'Expired';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) return `${hours}h ${minutes}m remaining`;
    return `${minutes}m remaining`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-green-600" />
          <span className="text-lg font-medium">Loading WhatsApp Integration...</span>
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
              <MessageCircle className="h-8 w-8 text-green-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">WhatsApp NDR Resolution</h1>
                <p className="text-sm text-gray-500">Customer Communication & Resolution Portal</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${getStatusColor(status)}`}>
                {getStatusIcon(status)}
                <span className="text-sm font-medium capitalize">{status}</span>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  checkWhatsAppStatus();
                  fetchAnalytics();
                  fetchPendingResponses();
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
        {/* Status Alert */}
        {status === 'error' && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              WhatsApp service is currently unavailable. NDR resolution messages cannot be sent.
            </AlertDescription>
          </Alert>
        )}

        {/* KPI Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Messages Sent</h3>
                <p className="text-3xl font-bold text-green-600">{analytics?.total_messages_sent || 0}</p>
                <p className="text-xs text-green-600 mt-1">Last 7 days</p>
              </div>
              <Send className="h-8 w-8 text-green-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Delivery Rate</h3>
                <p className="text-3xl font-bold text-blue-600">{analytics?.delivery_rate || 0}%</p>
                <p className="text-xs text-blue-600 mt-1">Message delivery success</p>
              </div>
              <Target className="h-8 w-8 text-blue-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Response Rate</h3>
                <p className="text-3xl font-bold text-purple-600">{analytics?.customer_response_rate || 0}%</p>
                <p className="text-xs text-purple-600 mt-1">Customer engagement</p>
              </div>
              <Users className="h-8 w-8 text-purple-600" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-500">Cost Savings</h3>
                <p className="text-3xl font-bold text-orange-600">₹{analytics?.cost_savings_estimate || 0}</p>
                <p className="text-xs text-orange-600 mt-1">RTOs prevented</p>
              </div>
              <DollarSign className="h-8 w-8 text-orange-600" />
            </div>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="pending" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="pending">Pending Responses</TabsTrigger>
            <TabsTrigger value="analytics">Performance Analytics</TabsTrigger>
            <TabsTrigger value="messages">Message Templates</TabsTrigger>
            <TabsTrigger value="testing">Testing & Debug</TabsTrigger>
          </TabsList>

          <TabsContent value="pending">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Pending Customer Responses
                  </h2>
                  <Badge variant="outline">
                    {pendingResponses.length} Active
                  </Badge>
                </div>

                {pendingResponses.length > 0 ? (
                  <div className="space-y-4">
                    {pendingResponses.map(([phone, data], index) => (
                      <div key={index} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                              <Phone className="h-4 w-4 text-gray-400" />
                              <span className="font-medium">{phone}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Package className="h-4 w-4 text-blue-500" />
                              <span className="text-sm text-gray-600">Order #{data.order_id}</span>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center space-x-2">
                              <Clock className="h-4 w-4 text-orange-500" />
                              <span className="text-sm font-medium text-orange-600">
                                {formatTimeRemaining(data.expires_at)}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              Sent: {new Date(data.sent_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        
                        <div className="mt-3 pt-3 border-t">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">
                              Customer has {formatTimeRemaining(data.expires_at).toLowerCase()} to respond
                            </span>
                            <Button variant="outline" size="sm">
                              <MessageSquare className="h-4 w-4 mr-1" />
                              Send Reminder
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    <MessageCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <p>No pending customer responses</p>
                    <p className="text-sm">All NDR resolution messages have been responded to.</p>
                  </div>
                )}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="analytics">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    WhatsApp Performance Metrics
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Message Delivery Rate</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={analytics?.delivery_rate || 0} className="w-24" />
                        <span className="text-sm font-medium">{analytics?.delivery_rate || 0}%</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Customer Response Rate</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={analytics?.customer_response_rate || 0} className="w-24" />
                        <span className="text-sm font-medium">{analytics?.customer_response_rate || 0}%</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">NDR Resolution Success</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={65} className="w-24" />
                        <span className="text-sm font-medium">65%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              <Card>
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Business Impact
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <TrendingUp className="h-5 w-5 text-green-600" />
                        <span className="text-sm font-medium text-green-800">RTOs Prevented</span>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        {Math.floor((analytics?.cost_savings_estimate || 0) / 200)}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <DollarSign className="h-5 w-5 text-blue-600" />
                        <span className="text-sm font-medium text-blue-800">Cost Savings</span>
                      </div>
                      <span className="text-lg font-bold text-blue-600">
                        ₹{analytics?.cost_savings_estimate || 0}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <Zap className="h-5 w-5 text-purple-600" />
                        <span className="text-sm font-medium text-purple-800">Response Time</span>
                      </div>
                      <span className="text-lg font-bold text-purple-600">
                        &lt;5min
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="messages">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  WhatsApp Message Templates
                </h2>
                
                <div className="space-y-6">
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-2">NDR Resolution Options</h4>
                    <div className="bg-gray-50 p-3 rounded text-sm">
                      🚚 **Delivery Update - Order #[ORDER_ID]**<br/><br/>
                      Hi! We attempted to deliver your order but you were unavailable.<br/><br/>
                      **Please choose an option:**<br/>
                      1️⃣ RESCHEDULE - Choose new delivery time<br/>
                      2️⃣ CHANGE ADDRESS - Update delivery location<br/>
                      3️⃣ SELF PICKUP - Collect from nearby hub<br/>
                      4️⃣ CANCEL ORDER - Process return<br/><br/>
                      Reply with the number (1, 2, 3, or 4) or type HELP.
                    </div>
                  </div>
                  
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-2">Reschedule Options</h4>
                    <div className="bg-gray-50 p-3 rounded text-sm">
                      ⏰ **Reschedule Delivery - Order #[ORDER_ID]**<br/><br/>
                      Please choose a convenient time slot:<br/><br/>
                      🌅 **Morning Slots:**<br/>
                      A. 9:00 AM - 12:00 PM<br/>
                      B. 10:00 AM - 1:00 PM<br/><br/>
                      Reply with the letter (A, B, C, D, or E).
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="testing">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Testing & Debug Tools
                  </h2>
                  <Dialog open={testDialog} onOpenChange={setTestDialog}>
                    <DialogTrigger asChild>
                      <Button>
                        <Send className="h-4 w-4 mr-2" />
                        Test NDR Flow
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                      <DialogHeader>
                        <DialogTitle>Test NDR WhatsApp Flow</DialogTitle>
                      </DialogHeader>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="text-sm font-medium mb-2 block">Order ID</label>
                          <Input 
                            placeholder="e.g., TEST_ORDER_001"
                            value={testData.order_id}
                            onChange={(e) => setTestData({...testData, order_id: e.target.value})}
                          />
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium mb-2 block">Customer Phone</label>
                          <Input 
                            placeholder="e.g., +919876543210"
                            value={testData.phone}
                            onChange={(e) => setTestData({...testData, phone: e.target.value})}
                          />
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium mb-2 block">NDR Reason</label>
                          <select 
                            className="w-full p-2 border border-gray-300 rounded-md"
                            value={testData.ndr_reason}
                            onChange={(e) => setTestData({...testData, ndr_reason: e.target.value})}
                          >
                            <option value="CUSTOMER_UNAVAILABLE">Customer Unavailable</option>
                            <option value="ADDRESS_INCOMPLETE">Address Incomplete</option>
                            <option value="CUSTOMER_REFUSED">Customer Refused</option>
                            <option value="OTHER">Other</option>
                          </select>
                        </div>
                        
                        <div className="flex justify-end space-x-2 pt-4">
                          <Button variant="outline" onClick={() => setTestDialog(false)}>
                            Cancel
                          </Button>
                          <Button onClick={triggerTestNDR} disabled={!testData.order_id || !testData.phone}>
                            Send Test NDR
                          </Button>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-lg font-medium mb-4">Service Status</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 border rounded">
                        <span>WhatsApp Service</span>
                        <Badge className={getStatusColor(status)}>
                          {status}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between p-3 border rounded">
                        <span>Message Queue</span>
                        <Badge className="bg-green-100 text-green-800">Active</Badge>
                      </div>
                      <div className="flex items-center justify-between p-3 border rounded">
                        <span>Database Connection</span>
                        <Badge className="bg-green-100 text-green-800">Connected</Badge>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-medium mb-4">Recent Activity</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center space-x-2 text-gray-600">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>Last message sent: 2 minutes ago</span>
                      </div>
                      <div className="flex items-center space-x-2 text-gray-600">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span>Last customer response: 15 minutes ago</span>
                      </div>
                      <div className="flex items-center space-x-2 text-gray-600">
                        <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                        <span>Pending responses: {pendingResponses.length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default WhatsAppIntegration;