// Shared error page layout for application error states.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

interface ErrorPageProps {
  code: number | string;
  title: string;
  message: string;
  buttonText: string;
  redirectPath: string;
}

export default function ErrorPage({ code, title, message, buttonText, redirectPath }: ErrorPageProps) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="relative text-center max-w-2xl mx-auto flex flex-col items-center">
        {/* Large Background Code */}
        <div className="text-[12rem] sm:text-[16rem] font-black text-gray-200/50 select-none leading-none absolute -top-16 sm:-top-24 -z-10 tracking-tighter">
          {code}
        </div>
        
        {/* Content */}
        <div className="z-10 mt-16 sm:mt-24 w-full flex flex-col items-center">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-6 drop-shadow-sm">
            {title}
          </h1>
          <div className="h-1 w-16 bg-[#F6BE00] mb-6 rounded-full mx-auto" />
          
          <p className="text-gray-600 mb-8 max-w-md text-base sm:text-lg text-center drop-shadow-sm">
            {message}
          </p>
          
          <Button 
            onClick={() => navigate(redirectPath)}
            className="bg-[#0A4D27] hover:bg-[#083c1e] text-white px-8 py-6 rounded-lg text-lg font-medium shadow-sm transition-all focus:ring-4 focus:ring-[#0A4D27]/20"
          >
            {buttonText}
          </Button>
        </div>
      </div>
      
      <div className="mt-24 text-center text-sm text-gray-400">
        &copy; {new Date().getFullYear()} Central Mindanao University
      </div>
    </div>
  );
}
