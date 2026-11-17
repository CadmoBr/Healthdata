
    
    

select
    sk_procedure as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."dim_procedure"
where sk_procedure is not null
group by sk_procedure
having count(*) > 1


