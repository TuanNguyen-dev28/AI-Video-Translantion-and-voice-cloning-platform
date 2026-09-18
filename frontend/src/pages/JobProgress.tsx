import React from 'react';

export const JobProgress = ({ jobId }: { jobId: string }) => {
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">Job Progress: {jobId}</h1>
            <p>Real-time updates via WebSocket/SSE...</p>
        </div>
    );
};
