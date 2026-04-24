import React from 'react';
import ErrorPage from './ErrorPage';

export default function Error500Page() {
  return (
    <ErrorPage
      code={500}
      title="Internal Server Error"
      message="Oops! Something went wrong on our end. Please try again later or contact the IT department if the issue persists."
      buttonText="Go Back to Home"
      redirectPath="/"
    />
  );
}
