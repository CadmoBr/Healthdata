
    
    

select
    sk_facility as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."dim_health_facility"
where sk_facility is not null
group by sk_facility
having count(*) > 1


