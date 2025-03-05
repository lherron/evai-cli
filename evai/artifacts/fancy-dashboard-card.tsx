import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, ArrowUpRight, BarChart2, Clock, Download, Users } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const FancyDashboardCard = () => {
  const [view, setView] = useState('week');
  
  // Sample data
  const weekData = [
    { name: 'Mon', value: 420 },
    { name: 'Tue', value: 380 },
    { name: 'Wed', value: 510 },
    { name: 'Thu', value: 580 },
    { name: 'Fri', value: 550 },
    { name: 'Sat', value: 620 },
    { name: 'Sun', value: 670 },
  ];
  
  const monthData = [
    { name: 'Week 1', value: 2800 },
    { name: 'Week 2', value: 3200 },
    { name: 'Week 3', value: 3600 },
    { name: 'Week 4', value: 3900 },
  ];
  
  const displayData = view === 'week' ? weekData : monthData;
  const currentValue = displayData[displayData.length - 1].value;
  const previousValue = displayData[displayData.length - 2].value;
  const percentChange = ((currentValue - previousValue) / previousValue * 100).toFixed(1);
  const isPositive = currentValue > previousValue;
  
  return (
    <Card className="w-full max-w-md shadow-lg">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-2xl font-bold">User Activity</CardTitle>
            <CardDescription className="text-gray-500">Daily active users</CardDescription>
          </div>
          <Badge variant="outline" className="flex items-center gap-1 px-2 py-1">
            <Users size={14} />
            <span>Users</span>
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="pb-0">
        <div className="flex items-baseline justify-between mb-4">
          <div>
            <span className="text-3xl font-bold">{currentValue}</span>
            <div className="flex items-center gap-1 mt-1">
              <Badge className={`${isPositive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                <span className="flex items-center gap-1">
                  {isPositive ? '+' : ''}{percentChange}%
                  <ArrowUpRight size={14} className={`${!isPositive && 'rotate-180'}`} />
                </span>
              </Badge>
              <span className="text-gray-500 text-sm">vs previous</span>
            </div>
          </div>
          
          <Tabs defaultValue="week" className="w-fit" onValueChange={setView}>
            <TabsList className="grid w-36 grid-cols-2">
              <TabsTrigger value="week">Week</TabsTrigger>
              <TabsTrigger value="month">Month</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={displayData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} width={30} />
              <Tooltip 
                contentStyle={{ 
                  borderRadius: '8px', 
                  border: 'none', 
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  padding: '8px 12px'
                }} 
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#6366F1" 
                strokeWidth={3} 
                dot={{ r: 4, strokeWidth: 2 }}
                activeDot={{ r: 6, stroke: '#6366F1', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {isPositive && percentChange > 15 && (
          <Alert className="mt-4 bg-amber-50">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertTitle>Notable increase</AlertTitle>
            <AlertDescription>
              User activity has increased significantly. Check system resources.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
      
      <CardFooter className="flex justify-between pt-4">
        <Button variant="outline" size="sm" className="gap-1">
          <Download size={14} />
          Export
        </Button>
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Clock size={14} />
          <span>Updated 2 mins ago</span>
        </div>
      </CardFooter>
    </Card>
  );
};

export default FancyDashboardCard;