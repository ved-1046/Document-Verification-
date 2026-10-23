import os

def update_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    newline = '\r\n' if '\r\n' in content else '\n'
    
    for old, new in replacements:
        # Normalize old/new to match file's newlines for finding
        old_norm = old.replace('\r\n', '\n').replace('\n', newline)
        new_norm = new.replace('\r\n', '\n').replace('\n', newline)
        if old_norm in content:
            content = content.replace(old_norm, new_norm, 1)
        else:
            print(f"Warning: target not found in {path}: {old[:40]}...")
            
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f"Updated {path}")

# 1. RequestDetailPage.tsx
update_file('frontend/src/pages/RequestDetailPage.tsx', [
    (
        "    AlertCircle,\n} from 'lucide-react';",
        "    AlertCircle,\n    Sparkles,\n} from 'lucide-react';"
    ),
    (
        '''                <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 text-xs font-bold ${request.status === 'approved' ? 'badge-approved' : request.status === 'rejected' || request.status === 'processing_failed' ? 'badge-failed' : request.status === 'more_info_required' ? 'badge-more-info' : request.status === 'under_review' || request.status === 'pending_approval' ? 'badge-review' : request.status === 'processing' ? 'badge-processing' : 'badge-submitted'}`}>''',
        '''                <div className="flex items-center gap-3">
                    <Link
                        to={`/assistant?requestId=${request.id}`}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-violet-200 bg-violet-50 px-3.5 py-1.5 text-xs font-bold text-[#7656D6] hover:bg-violet-100 transition shadow-2xs"
                        title="Open AI Assistant for this claim"
                    >
                        <Sparkles className="h-3.5 w-3.5 text-[#7656D6]" />
                        <span>Ask AI Assistant</span>
                    </Link>
                    <span className={`px-3 py-1 text-xs font-bold ${request.status === 'approved' ? 'badge-approved' : request.status === 'rejected' || request.status === 'processing_failed' ? 'badge-failed' : request.status === 'more_info_required' ? 'badge-more-info' : request.status === 'under_review' || request.status === 'pending_approval' ? 'badge-review' : request.status === 'processing' ? 'badge-processing' : 'badge-submitted'}`}>'''
    )
])

# 2. SubmitterClaimView.tsx
update_file('frontend/src/components/SubmitterClaimView.tsx', [
    (
        '''                    <Link
                        to="/assistant"''',
        '''                    <Link
                        to={`/assistant?requestId=${request.id}`}'''
    )
])

# 3. ReviewerClaimView.tsx
update_file('frontend/src/components/ReviewerClaimView.tsx', [
    (
        "import { useState } from 'react';",
        "import { useState } from 'react';\nimport { Link } from 'react-router-dom';"
    ),
    (
        "    ChevronDown,\n} from 'lucide-react';",
        "    ChevronDown,\n    Sparkles,\n} from 'lucide-react';"
    ),
    (
        '''                    <div className="flex flex-wrap items-center gap-2.5">
                        <button
                            type="button"
                            onClick={onOpenGraph}''',
        '''                    <div className="flex flex-wrap items-center gap-2.5">
                        <Link
                            to={`/assistant?requestId=${request.id}`}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600/90 hover:bg-violet-600 px-3.5 py-2 text-xs font-bold text-white transition shadow-xs"
                            title="Open AI Assistant to audit this claim"
                        >
                            <Sparkles className="h-4 w-4 text-violet-200" />
                            <span>Ask AI Assistant</span>
                        </Link>
                        <button
                            type="button"
                            onClick={onOpenGraph}'''
    )
])

# 4. ApproverClaimView.tsx
update_file('frontend/src/components/ApproverClaimView.tsx', [
    (
        "import { useState } from 'react';",
        "import { useState } from 'react';\nimport { Link } from 'react-router-dom';"
    ),
    (
        "    UserCheck,\n} from 'lucide-react';",
        "    UserCheck,\n    Sparkles,\n} from 'lucide-react';"
    ),
    (
        '''                    <div className="flex flex-wrap items-center gap-2.5">
                        <button
                            type="button"
                            onClick={onOpenGraph}''',
        '''                    <div className="flex flex-wrap items-center gap-2.5">
                        <Link
                            to={`/assistant?requestId=${request.id}`}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-violet-600/90 hover:bg-violet-600 px-3.5 py-2 text-xs font-bold text-white transition shadow-xs"
                            title="Open AI Assistant for executive summary"
                        >
                            <Sparkles className="h-4 w-4 text-violet-200" />
                            <span>Ask AI Assistant</span>
                        </Link>
                        <button
                            type="button"
                            onClick={onOpenGraph}'''
    )
])
