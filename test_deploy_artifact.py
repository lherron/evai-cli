#!/usr/bin/env python
"""Test script for the deploy_artifact tool."""

from evai.tool_storage import run_tool
import json

# Sample React component
component = '''
import React from 'react';
import { Button } from '@/components/ui/button';

interface ButtonProps {
  label: string;
  onClick: () => void;
}

export const CustomButton: React.FC<ButtonProps> = ({ label, onClick }) => {
  return (
    <Button 
      className='bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded'
      onClick={onClick}
    >
      {label}
    </Button>
  );
};
'''

# Run the deploy_artifact tool
result = run_tool('deploy_artifact', artifact_name='CustomButton', source_code=component)
print(json.dumps(result, indent=2)) 