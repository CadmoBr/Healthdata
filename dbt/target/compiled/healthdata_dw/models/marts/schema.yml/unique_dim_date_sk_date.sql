
    
    

select
    sk_date as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."dim_date"
where sk_date is not null
group by sk_date
having count(*) > 1


