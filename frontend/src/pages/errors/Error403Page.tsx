/** Error403Page — unauthorized access to a role-restricted resource. */
import React from 'react';
import ErrorPage from './ErrorPage';

export default function Error403Page() {
  return (
    <ErrorPage
      code={403}
      title="403 - Unauthorized"
      message="You do not have permission to access this resource. Please contact your administrator if you believe this is an error."
      buttonText="Go to Dashboard"
      redirectPath="/"
    />
  );
}
