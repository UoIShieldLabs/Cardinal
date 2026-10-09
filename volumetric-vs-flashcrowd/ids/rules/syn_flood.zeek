@load base/frameworks/notice

module SYNFlood;

export {
    redef enum Notice::Type += { SYN_Rate_Exceeded };
    const syn_rate_threshold = 200 &redef;
}

global syn_counts: table[addr] of count &default=0 &create_expire=10sec;

event connection_attempt(c: connection)
{
    local dst = c$id$resp_h;
    syn_counts[dst] += 1;

    if (syn_counts[dst] == syn_rate_threshold)
    {
        NOTICE([$note=SYN_Rate_Exceeded,
                $msg=fmt("SYN rate exceeded threshold to %s", dst),
                $id=c$id]);
    }
}