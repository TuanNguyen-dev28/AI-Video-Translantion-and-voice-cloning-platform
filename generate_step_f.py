import os

pages_dir = 'frontend/src/pages'
os.makedirs(pages_dir, exist_ok=True)

create_job = '''import React from 'react';

export const CreateJob = () => {
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">Create Translation Job</h1>
            <p>Paste URL here to start...</p>
        </div>
    );
};
'''
with open(os.path.join(pages_dir, 'CreateJob.tsx'), 'w', encoding='utf-8') as f: f.write(create_job)

dashboard = '''import React from 'react';

export const Dashboard = () => {
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">User Dashboard</h1>
            <p>Recent jobs, wallet balance, and quota usage.</p>
        </div>
    );
};
'''
with open(os.path.join(pages_dir, 'Dashboard.tsx'), 'w', encoding='utf-8') as f: f.write(dashboard)

progress = '''import React from 'react';

export const JobProgress = ({ jobId }: { jobId: string }) => {
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">Job Progress: {jobId}</h1>
            <p>Real-time updates via WebSocket/SSE...</p>
        </div>
    );
};
'''
with open(os.path.join(pages_dir, 'JobProgress.tsx'), 'w', encoding='utf-8') as f: f.write(progress)

admin = '''import React from 'react';

export const AdminDashboard = () => {
    return (
        <div className="p-4">
            <h1 className="text-2xl font-bold">Admin Panel</h1>
            <p>Manage all users, view system metrics, and force-retry failed jobs.</p>
        </div>
    );
};
'''
with open(os.path.join(pages_dir, 'AdminDashboard.tsx'), 'w', encoding='utf-8') as f: f.write(admin)

