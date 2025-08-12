import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';

// Import components
import { Card } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Progress } from './components/ui/progress';
import { Alert, AlertDescription } from './components/ui/alert';

// Import new components
import SellerDashboard from './components/SellerDashboard';
import WhatsAppIntegration from './components/WhatsAppIntegration';

// Icons from lucide-react
import { 
  TrendingUp, 
  TrendingDown, 
  Package, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  BarChart3,
  Users,
  MapPin,
  Phone,
  RefreshCw,
  Shield,
  MessageCircle,
  Settings
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [kpiData, setKpiData] = useState({
    rto_rate: 0,
    adoption_rate: 0,
    delay_vs_promise: 0,
    cod_to_prepaid: 0,
    false_attempt_rate: 0,
    suspect_ndr_rate: 0
  });

  const [scorecardData, setScorecardData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    fetchKPIs();
    fetchScorecard();
    // Refresh data every 5 minutes
    const interval = setInterval(() => {
      fetchKPIs();
      fetchScorecard();
    }, 300000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchKPIs = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/kpis`);
      if (response.ok) {
        const data = await response.json();
        setKpiData(data);
      } else {
        // Fallback to mock data if API fails
        setKpiData({
          rto_rate: 12.5,
          adoption_rate: 78.3,
          delay_vs_promise: -2.1,
          cod_to_prepaid: 15.7,
          false_attempt_rate: 8.2,
          suspect_ndr_rate: 4.1
        });
      }
    } catch (err) {
      setError('Failed to fetch KPI data');
      // Fallback to mock data
      setKpiData({
        rto_rate: 12.5,
        adoption_rate: 78.3,
        delay_vs_promise: -2.1,
        cod_to_prepaid: 15.7,
        false_attempt_rate: 8.2,
        suspect_ndr_rate: 4.1
      });
    }
  };

  const fetchScorecard = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/scorecard`);
      if (response.ok) {
        const data = await response.json();
        setScorecardData(data);
        setLoading(false);
        setLastUpdated(new Date());
      } else {
        // Fallback to mock data
        setScorecardData([
          {
            carrier: 'Delhivery',
            dest_pin: '560001',
            week: '2024-W01',
            total_shipments: 1250,
            on_time_percentage: 85.2,
            rto_percentage: 8.5,
            false_attempt_rate: 5.1,
            suspect_ndr_rate: 2.8,
            first_attempt_percentage: 78.9
          },
          {
            carrier: 'Shiprocket',
            dest_pin: '560002',
            week: '2024-W01',
            total_shipments: 890,
            on_time_percentage: 79.3,
            rto_percentage: 12.1,
            false_attempt_rate: 9.8,
            suspect_ndr_rate: 6.2,
            first_attempt_percentage: 72.4
          },
          {
            carrier: 'Delhivery',
            dest_pin: '560003',
            week: '2024-W01',
            total_shipments: 675,
            on_time_percentage: 88.7,
            rto_percentage: 6.3,
            false_attempt_rate: 4.2,
            suspect_ndr_rate: 1.9,
            first_attempt_percentage: 82.1
          }
        ]);
        setLoading(false);
        setLastUpdated(new Date());
      }
    } catch (err) {
      setError('Failed to fetch scorecard data');
      setLoading(false);
    }
  };

  const getKPIIcon = (metric) => {
    switch (metric) {
      case 'rto_rate': return <Package className="h-6 w-6" />;
      case 'adoption_rate': return <Users className="h-6 w-6" />;
      case 'delay_vs_promise': return <Clock className="h-6 w-6" />;
      case 'cod_to_prepaid': return <TrendingUp className="h-6 w-6" />;
      case 'false_attempt_rate': return <AlertTriangle className="h-6 w-6" />;
      case 'suspect_ndr_rate': return <XCircle className="h-6 w-6" />;
      default: return <BarChart3 className="h-6 w-6" />;
    }
  };

  const getKPITitle = (metric) => {
    switch (metric) {
      case 'rto_rate': return 'RTO Rate';
      case 'adoption_rate': return 'Adoption Rate';
      case 'delay_vs_promise': return 'Delay vs Promise';
      case 'cod_to_prepaid': return 'COD→Prepaid';
      case 'false_attempt_rate': return 'False Attempt Rate';
      case 'suspect_ndr_rate': return 'Suspect NDR Rate';
      default: return metric;
    }
  };

  const getKPIColor = (metric, value) => {
    const goodMetrics = ['adoption_rate', 'cod_to_prepaid'];
    const badMetrics = ['rto_rate', 'false_attempt_rate', 'suspect_ndr_rate'];
    
    if (goodMetrics.includes(metric)) {
      return value > 70 ? 'text-green-600' : value > 50 ? 'text-yellow-600' : 'text-red-600';
    } else if (badMetrics.includes(metric)) {
      return value < 5 ? 'text-green-600' : value < 10 ? 'text-yellow-600' : 'text-red-600';
    }
    return 'text-blue-600';
  };

  const getRiskBadge = (rate, thresholds) => {
    if (rate >= thresholds.high) {
      return <Badge variant="destructive">High Risk</Badge>;
    } else if (rate >= thresholds.medium) {
      return <Badge variant="secondary">Medium Risk</Badge>;
    } else {
      return <Badge variant="default" className="bg-green-100 text-green-800">Low Risk</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-blue-600" />
          <span className="text-lg font-medium">Loading RTO Optimizer...</span>
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
              <Package className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">RTO Optimizer</h1>
                <p className="text-sm text-gray-500">Bengaluru PoC Dashboard</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  fetchKPIs();
                  fetchScorecard();
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {Object.entries(kpiData).map(([metric, value]) => (
            <Card key={metric} className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="text-blue-600">
                    {getKPIIcon(metric)}
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">
                      {getKPITitle(metric)}
                    </h3>
                    <p className={`text-2xl font-bold ${getKPIColor(metric, value)}`}>
                      {metric === 'delay_vs_promise' && value > 0 ? '+' : ''}
                      {value}%{metric === 'delay_vs_promise' ? ' hrs' : ''}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {value > 0 ? (
                    <TrendingUp className="h-5 w-5 text-green-500" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-red-500" />
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Tabs for different views */}
        <Tabs defaultValue="scorecard" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="scorecard">Weekly Scorecard</TabsTrigger>
            <TabsTrigger value="alerts">Alerts & Monitoring</TabsTrigger>
            <TabsTrigger value="settings">Lane Allocation</TabsTrigger>
          </TabsList>

          <TabsContent value="scorecard">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">
                    Weekly Carrier Performance Scorecard
                  </h2>
                  <Badge variant="outline">Current Week: 2024-W01</Badge>
                </div>

                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Carrier</TableHead>
                        <TableHead>Dest PIN</TableHead>
                        <TableHead>Total Shipments</TableHead>
                        <TableHead>On-Time %</TableHead>
                        <TableHead>RTO %</TableHead>
                        <TableHead>FAR %</TableHead>
                        <TableHead>Suspect NDR %</TableHead>
                        <TableHead>First Attempt %</TableHead>
                        <TableHead>Risk Level</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scorecardData.map((row, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{row.carrier}</TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-1">
                              <MapPin className="h-4 w-4 text-gray-400" />
                              <span>{row.dest_pin}</span>
                            </div>
                          </TableCell>
                          <TableCell>{row.total_shipments.toLocaleString()}</TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <Progress value={row.on_time_percentage} className="w-16" />
                              <span className="text-sm font-medium">
                                {row.on_time_percentage}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className={
                              row.rto_percentage < 8 ? 'text-green-600' :
                              row.rto_percentage < 12 ? 'text-yellow-600' : 'text-red-600'
                            }>
                              {row.rto_percentage}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={
                              row.false_attempt_rate < 5 ? 'text-green-600' :
                              row.false_attempt_rate < 10 ? 'text-yellow-600' : 'text-red-600'
                            }>
                              {row.false_attempt_rate}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={
                              row.suspect_ndr_rate < 3 ? 'text-green-600' :
                              row.suspect_ndr_rate < 6 ? 'text-yellow-600' : 'text-red-600'
                            }>
                              {row.suspect_ndr_rate}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              <Progress value={row.first_attempt_percentage} className="w-16" />
                              <span className="text-sm font-medium">
                                {row.first_attempt_percentage}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            {getRiskBadge(
                              Math.max(row.false_attempt_rate, row.suspect_ndr_rate),
                              { medium: 5, high: 10 }
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
                  Active Alerts & Monitoring
                </h2>

                <div className="space-y-4">
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>High FAR Alert:</strong> Shiprocket in PIN 560002 has FAR of 9.8% 
                      (threshold: 10%). Monitor closely.
                    </AlertDescription>
                  </Alert>

                  <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Performance Good:</strong> Delhivery in PIN 560003 maintaining 
                      excellent metrics across all KPIs.
                    </AlertDescription>
                  </Alert>

                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Suspect NDR Alert:</strong> Shiprocket in PIN 560002 has Suspect NDR 
                      rate of 6.2% (threshold: 5%). Investigation required.
                    </AlertDescription>
                  </Alert>
                </div>

                <div className="mt-8">
                  <h3 className="text-lg font-medium mb-4">Alert Thresholds</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card className="p-4">
                      <h4 className="font-medium text-red-600 mb-2">False Attempt Rate</h4>
                      <p className="text-sm text-gray-600">
                        Medium: ≥10% | High: ≥15%
                      </p>
                    </Card>
                    <Card className="p-4">
                      <h4 className="font-medium text-red-600 mb-2">Suspect NDR Rate</h4>
                      <p className="text-sm text-gray-600">
                        Medium: ≥5% | High: ≥8%
                      </p>
                    </Card>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="settings">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Lane Allocation Weights
                </h2>
                
                <div className="space-y-6">
                  <div>
                    <p className="text-gray-600 mb-4">
                      Configure carrier selection weights for different PIN codes and performance metrics.
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="p-4">
                      <h3 className="font-medium mb-3">Performance Weights</h3>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm">On-time Delivery</span>
                          <Badge variant="outline">40%</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">RTO Rate</span>
                          <Badge variant="outline">30%</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">False Attempt Rate</span>
                          <Badge variant="outline">20%</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">First Attempt Success</span>
                          <Badge variant="outline">10%</Badge>
                        </div>
                      </div>
                    </Card>

                    <Card className="p-4">
                      <h3 className="font-medium mb-3">Carrier Priority</h3>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Delhivery</span>
                          <Badge className="bg-green-100 text-green-800">Primary</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Shiprocket</span>
                          <Badge variant="secondary">Secondary</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">BlueDart</span>
                          <Badge variant="outline">Backup</Badge>
                        </div>
                      </div>
                    </Card>
                  </div>

                  <div className="mt-6">
                    <Button variant="outline" className="mr-2">
                      Edit Weights
                    </Button>
                    <Button>
                      Save Configuration
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;