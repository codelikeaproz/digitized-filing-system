/**
 * AutoLogout — idle timeout; clears session after inactivity (default 10 min).
 */
import React, { useCallback, useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';

export default function AutoLogout({ timeoutMinutes = 10 }: { timeoutMinutes?: number }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleLogout = useCallback(() => {
    logout();
    toast("You were logged out due to inactivity.");
    navigate("/login");
  }, [logout, navigate]);

  const resetTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // Only run timer if user is logged in and not already on the login page
    if (user && location.pathname !== '/login') {
      timeoutRef.current = setTimeout(handleLogout, timeoutMinutes * 60 * 1000);
    }
  }, [handleLogout, location.pathname, timeoutMinutes, user]);

  useEffect(() => {
    // Initial setup
    resetTimer();

    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    
    const handleUserActivity = () => {
      // Debounce the reset to avoid running it too often (optional but good practice)
      // For simplicity, we just reset it directly here.
      resetTimer();
    };

    events.forEach(event => {
      window.addEventListener(event, handleUserActivity);
    });

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      events.forEach(event => {
        window.removeEventListener(event, handleUserActivity);
      });
    };
  }, [resetTimer]);

  return <></>; // render nothing
}
