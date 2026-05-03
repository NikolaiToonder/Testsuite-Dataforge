import React from 'react';

export const useSearchParams = () => {
  const [params, setParamsState] = React.useState(new URLSearchParams());

  const setSearchParams = (next: Record<string, string>) => {
    setParamsState(new URLSearchParams(next));
  };

  return [params, setSearchParams] as const;
};