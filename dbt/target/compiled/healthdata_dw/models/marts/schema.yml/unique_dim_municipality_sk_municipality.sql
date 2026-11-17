
    
    

select
    sk_municipality as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."dim_municipality"
where sk_municipality is not null
group by sk_municipality
having count(*) > 1


