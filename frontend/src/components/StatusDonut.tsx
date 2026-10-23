import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface StatusDatum {
    name: string;
    value: number;
    color: string;
}

export default function StatusDonut({ data, total }: { data: StatusDatum[]; total: number }) {
    return (
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
            <div className="relative h-[200px] w-full max-w-[210px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={data}
                            dataKey="value"
                            nameKey="name"
                            innerRadius={58}
                            outerRadius={82}
                            paddingAngle={3}
                            stroke="none"
                        >
                            {data.map((entry) => (
                                <Cell key={entry.name} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip
                            formatter={(value, name) => [`${value} claims`, name]}
                            contentStyle={{
                                borderRadius: '12px',
                                border: '1px solid #E3E8F0',
                                backgroundColor: '#FFFFFF',
                                color: '#20263A',
                                fontSize: '11px',
                                fontWeight: 600,
                                boxShadow: '0 4px 12px rgba(23, 37, 84, 0.08)',
                            }}
                        />
                    </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    <strong className="text-2xl font-black text-main">{total}</strong>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted">total claims</span>
                </div>
            </div>

            <ul className="w-full space-y-2">
                {data.slice(0, 6).map((item) => (
                    <li key={item.name} className="flex items-center justify-between gap-3 text-xs">
                        <span className="flex items-center gap-2 font-medium text-slate-700">
                            <span
                                className="h-2.5 w-2.5 rounded-full shrink-0 shadow-xs"
                                style={{ backgroundColor: item.color }}
                            />
                            {item.name}
                        </span>
                        <strong className="font-bold text-main">{item.value}</strong>
                    </li>
                ))}
            </ul>
        </div>
    );
}
