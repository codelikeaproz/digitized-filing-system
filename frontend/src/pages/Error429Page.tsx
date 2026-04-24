import React from 'react';
import ErrorPage from './ErrorPage';

export default function Error429Page() {
  return (
    <ErrorPage
      code={429}
      title="Too Many Requests"
      message="Too many login attempts. Please wait a moment before trying again."
      buttonText="Go Back to Login"
      redirectPath="/login"
    />
  );
}
