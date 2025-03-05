
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
